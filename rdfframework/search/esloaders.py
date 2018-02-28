__author__ = "Mike Stabile, Jeremy Nelson"
import time
import datetime
import inspect
import logging
import gc
import os
# import os
# import rdflib
# import requests
# import sys
# import uuid
import pdb
# import urllib
import time
# import queue
import threading
# import json
# import socket
import copy
import json

try:
    MNAME = inspect.stack()[0][1]
except:
    MNAME = "esloaders"
MLOG_LVL = logging.DEBUG
logging.basicConfig(level=logging.DEBUG)
lg_r = logging.getLogger("requests")
lg_r.setLevel(logging.CRITICAL)

from rdfframework.utilities import DataStatus, pp, render_without_request
from rdfframework.configuration import RdfConfigManager
from rdfframework.sparql import get_all_item_data
from rdfframework.search import EsBase, EsMappings
from rdfframework.datasets import RdfDataset
from rdfframework.datatypes import RdfNsManager, Uri, pyrdf

CFG = RdfConfigManager()
NSM = RdfNsManager()

class EsRdfBulkLoader(object):
    """ Bulk loads data from the triplestore to elasticsearch """

    log_level = logging.DEBUG
    items_query_template = """
        SELECT DISTINCT ?s
        {{
            VALUES ?rdftypes {{\n\t\t{} }} .
            ?s a ?rdftypes .
        }} """

    def __init__(self, rdf_class, tstore_conn, search_conn):
        log.setLevel(self.log_level)
        self.tstore_conn = tstore_conn
        self.search_conn = search_conn
        self.es_index = rdf_class.es_defs.get('kds_esIndex')[0]
        self.es_doc_type = rdf_class.es_defs.get('kds_esDocType')[0]
        new_esbase = copy.copy(self.search_conn)
        new_esbase.es_index = self.es_index
        new_esbase.doc_type = self.es_doc_type
        log.info("Indexing '%s' into ES index '%s' doctype '%s'",
                 rdf_class.__name__,
                 self.es_index,
                 self.es_doc_type)
        self.es_worker = new_esbase
        self.rdf_class = rdf_class
        # add all of the sublcasses for a rdf_class
        rdf_types = [rdf_class.uri] + [item.uri
                                       for item in rdf_class.subclasses]
        self.query = self.items_query_template.format("\n\t\t".join(rdf_types))
        EsMappings().initialize_indices()
        self.count = 0
        self._index_group_with_subgroup()


    def _index_item(self, uri, num, batch_num):
        """ queries the triplestore for an item sends it to elasticsearch """

        data = RdfDataset(get_all_item_data(uri, self.tstore_conn),
                          uri).base_class.es_json()
        self.batch_data[batch_num].append(data)
        self.count += 1


    def _index_group(self):
        """ indexes all the URIs defined by the query into Elasticsearch """

        log.setLevel(self.log_level)
        # get a list of all the uri to index
        results = self.tstore_conn.query(sparql=self.query)
        # results = results[:100]
        # Start processing through uri
        self.time_start = datetime.datetime.now()
        batch_size = 12000
        if len(results) > batch_size:
            batch_end = batch_size
        else:
            batch_end = len(results)
        batch_start = 0
        batch_num = 1
        self.batch_data = {}
        self.batch_data[batch_num] = []
        end = False
        last = False
        while not end:
            log.debug("batch %s: %s-%s", batch_num, batch_start, batch_end)
            for i, subj in enumerate(results[batch_start:batch_end]):
                th = threading.Thread(name=batch_start + i + 1,
                                      target=self._index_item,
                                      args=(MSN.iri(subj['s']['value']),
                                            i+1,batch_num,))
                th.start()
            log.debug(datetime.datetime.now() - self.time_start)
            main_thread = threading.main_thread()
            for t in threading.enumerate():
                if t is main_thread:
                    continue
                t.join()
            action_list = \
                    self.es_worker.make_action_list(self.batch_data[batch_num])
            self.es_worker.bulk_save(action_list)
            del self.batch_data[batch_num]
            batch_end += batch_size
            batch_start += batch_size
            if last:
                end = True
            if len(results) <= batch_end:
                batch_end = len(results)
                last = True
            batch_num += 1
            self.batch_data[batch_num] = []
            log.debug(datetime.datetime.now() - self.time_start)

    def _index_sub(self, uri_list, num, batch_num):
        """
        Converts a list of uris to eslasticsearch json objects

        args:
            uri_list: list of uris to convert
            num: the ending count within the batch
            batch_num: the batch number
        """
        bname = '%s-%s' % (batch_num, num)
        log.debug("batch_num '%s' starting es_json conversion",
                  bname)
        qry_data = get_all_item_data(uri_list,
                                     self.tstore_conn,
                                     rdfclass=self.rdf_class)
        log.debug("batch_num '%s-%s' query_complete | count: %s",
                  batch_num,
                  num,
                  len(qry_data))
        path = os.path.join(CFG.dirs.cache, "index_pre")
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, bname + ".json"), "w") as fo:
            fo.write(json.dumps(qry_data))
        data = RdfDataset(qry_data)
        del qry_data
        log.debug("batch_num '%s-%s' RdfDataset Loaded", batch_num, num)
        # pdb.set_trace()
        for value in uri_list:
            try:

                self.batch_data[batch_num].append(\
                        data[value].es_json())
                self.count += 1
            except KeyError:
                pass
        del data
        del uri_list
        log.debug("butch_num '%s-%s' converted to es_json", batch_num, num)

    def _get_uri_list(self):
        """
        Returns a list of Uris to index
        """
        results = [Uri(item['s']['value'])
                   for item in self.tstore_conn.query(sparql=self.query)]
        return results

    def _index_group_with_subgroup(self):
        """ indexes all the URIs defined by the query into Elasticsearch """

        log.setLevel(self.log_level)
        # get a list of all the uri to index
        uri_list = self._get_uri_list()
        # results = results[:100]
        # Start processing through uri
        batch_file = os.path.join(CFG.dirs.logs, "batch_list.txt")
        with open(batch_file, "w") as fo:
            fo.write("{")
        log.info("'%s' items to index", len(uri_list))
        self.time_start = datetime.datetime.now()
        batch_size = 12000
        if len(uri_list) > batch_size:
            batch_end = batch_size
        else:
            batch_end = len(uri_list)
        batch_start = 0
        batch_num = 1
        self.batch_data = {}
        self.batch_data[batch_num] = []
        end = False
        last = False
        while not end:
            log.debug("batch %s: %s-%s", batch_num, batch_start, batch_end)
            sub_batch = []
            j = 0
            for i in range(batch_start, batch_end):
            # for i, subj in enumerate(uri_list[batch_start:batch_end]):
                qry_size = 1000
                if j < qry_size:
                    try:
                        sub_batch.append(uri_list.pop()) #subj)
                    except IndexError:
                        pass
                if j == qry_size -1 or i == batch_end - 1:
                    try:
                        sub_batch.append(uri_list.pop()) #subj)
                    except IndexError:
                        pass
                    with open(batch_file, "a") as fo:
                        fo.write(json.dumps({str('%s-%s' % (batch_num, i+1)):
                                             [item.sparql
                                              for item in sub_batch]})[1:-1]+",\n")
                    th = threading.Thread(name=batch_start + i + 1,
                                          target=self._index_sub,
                                          args=(sub_batch,
                                                i+1,batch_num,))
                    th.start()
                    # self._index_sub(sub_batch, i+1, batch_num)
                    j = 0
                    sub_batch = []
                else:
                    j += 1
            log.debug(datetime.datetime.now() - self.time_start)
            main_thread = threading.main_thread()
            for t in threading.enumerate():
                # pdb.set_trace()
                if t is main_thread:
                    continue
                t.join()
            action_list = \
                    self.es_worker.make_action_list(self.batch_data[batch_num])
            self.es_worker.bulk_save(action_list)
            del action_list
            del self.batch_data[batch_num]
            del pyrdf.memorized
            pyrdf.memorized = {}
            while gc.collect() > 0:
                pass
            # pdb.set_trace()
            batch_end += batch_size
            batch_start += batch_size
            if last:
                end = True
            if len(uri_list) <= batch_size:
                batch_end = len(uri_list)
                last = True
            batch_num += 1
            self.batch_data[batch_num] = []
            # log.debug("waiting 10 secs")
            # time.sleep(10)
            log.debug(datetime.datetime.now() - self.time_start)
        with open(batch_file, 'rb+') as fo:
            fo.seek(-2, os.SEEK_END)
            fo.truncate()
            # fo.close()
            fo.write("}".encode())
        # with open(batch_file, "a"):
        #     pass
        # with open(batch_file, "a"):
            # fo.write("}".encode())
