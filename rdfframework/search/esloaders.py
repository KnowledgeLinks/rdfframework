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
from rdfframework.datatypes import (RdfNsManager,
                                    Uri,
                                    pyrdf,
                                    XsdDatetime,
                                    XsdString)
from rdfframework.rdfclass import make_es_id

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
            optional {{ ?s dcterm:modified ?modTime }} .
            optional {{ ?s kds:esIndexTime ?time }} .
            optional {{ ?s kds:esIndexError ?error }}
            filter (!(bound(?time))||(?time<?modTime)||bound(?error))
        }} """

    def __init__(self, rdf_class, tstore_conn, search_conn, **kwargs):
        log.setLevel(self.log_level)
        self.tstore_conn = tstore_conn
        self.search_conn = search_conn
        self.es_index = rdf_class.es_defs.get('kds_esIndex')[0]
        self.es_doc_type = rdf_class.es_defs.get('kds_esDocType')[0]
        self.rdf_class = rdf_class
        self._set_es_workers()
        # add all of the sublcasses for a rdf_class
        rdf_types = [rdf_class.uri] + [item.uri
                                       for item in rdf_class.subclasses]
        self.query = self.items_query_template.format("\n\t\t".join(rdf_types))
        EsMappings().initialize_indices()
        self.count = 0
        self._index_group_with_subgroup(**kwargs)

    def _set_es_workers(self, **kwargs):
        """
        Creates index woorker instances for each class to index
        """
        def make_es_worker(search_conn, es_index, es_doc_type, class_name):
            """
            Returns a new es_worker instance
            """
            new_esbase = copy.copy(search_conn)
            new_esbase.es_index = es_index
            new_esbase.doc_type = es_doc_type
            log.info("Indexing '%s' into ES index '%s' doctype '%s'",
                     class_name,
                     es_index,
                     es_doc_type)
            return new_esbase

        def additional_indexers(rdf_class):
            """
            returns additional classes to index based off of the es definitions
            """
            rtn_list = rdf_class.es_indexers()
            rtn_list.remove(rdf_class)
            return rtn_list


        self.es_worker = make_es_worker(self.search_conn,
                                        self.es_index,
                                        self.es_doc_type,
                                        self.rdf_class.__name__)
        self.other_indexers = {item.__name__: make_es_worker(
                                        self.search_conn,
                                        item.es_defs.get('kds_esIndex')[0],
                                        item.es_defs.get('kds_esDocType')[0],
                                        item.__name__)
                               for item in additional_indexers(self.rdf_class)}
        # self.other_indexers = {}
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
        for value in uri_list:
            try:

                self.batch_data[batch_num]['main'].append(\
                        data[value].es_json())
                self.count += 1
            except KeyError:
                pass
        for name, indexer in self.other_indexers.items():
            for item in data.json_qry("$.:%s" % name.pyuri):
                val = item.es_json()
                if val:
                    self.batch_data[batch_num][name].append(val)
                    self.batch_uris[batch_num].append(item.subject)
        del data
        del uri_list
        log.debug("batch_num '%s-%s' converted to es_json", batch_num, num)

    def _get_uri_list(self):
        """
        Returns a list of Uris to index
        """
        results = [Uri(item['s']['value'])
                   for item in self.tstore_conn.query(sparql=self.query)]
        return results

    def _index_group_with_subgroup(self, **kwargs):
        """ indexes all the URIs defined by the query into Elasticsearch """

        log.setLevel(self.log_level)
        # get a list of all the uri to index
        uri_list = self._get_uri_list()
        if not uri_list:
            log.info("0 items to index")
            return
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
        self.batch_data[batch_num] = {}
        self.batch_data[batch_num]['main'] = []
        self.batch_uris = {}
        self.batch_uris[batch_num] = []
        for name, indexer in self.other_indexers.items():
            self.batch_data[batch_num][name] = []
        end = False
        last = False
        final_list = []
        expand_index = kwargs.get("expand_index", True)
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
                    if not kwargs.get("no_threading", False):
                        th = threading.Thread(name=batch_start + i + 1,
                                              target=self._index_sub,
                                              args=(sub_batch,
                                                    i+1,
                                                    batch_num,))
                        th.start()
                    else:
                        self._index_sub(sub_batch, i+1, batch_num)
                    j = 0
                    final_list += sub_batch
                    sub_batch = []
                else:
                    j += 1
            log.debug(datetime.datetime.now() - self.time_start)
            if not kwargs.get("no_threading", False):
                main_thread = threading.main_thread()
                for t in threading.enumerate():
                    if t is main_thread:
                        continue
                    t.join()
            action_list = []
            for key, items in self.batch_data[batch_num].items():
                if key == 'main':
                    es_worker = self.es_worker
                else:
                    es_worker = self.other_indexers[key]
                action_list += es_worker.make_action_list(items)
            result = self.es_worker.bulk_save(action_list)
            final_list += self.batch_uris[batch_num]
            self._update_triplestore(result, action_list)
            del action_list
            del self.batch_uris[batch_num]
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
            self.batch_uris[batch_num] = []
            self.batch_data[batch_num] = {}
            self.batch_data[batch_num]['main'] = []
            for name, indexer in self.other_indexers.items():
                self.batch_data[batch_num][name] = []
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
    def _update_triplestore(self, es_result, action_list, **kwargs):
        """
        updates the triplestore with succes of saves and failues of indexing

        Args:
        -----
            es_result: the elasticsearch result list
            uri_list: the uri's that were indexed
        """
        idx_time = XsdDatetime(datetime.datetime.utcnow())
        uri_keys = {}
        bnode_keys = {}
        for item in action_list:
            try:
                uri_keys[item['_id']] = item['_source']["uri"]
            except KeyError:
                bnode_keys[item['_id']] = item['_id']
        # uri_keys = {make_es_id(item): item for item in uri_list}
        error_dict = {}
        error_bnodes = {}
        if es_result[1]:
            for result in es_result[1]:
                err_item = list(result.values())[0]
                try:
                    error_dict[uri_keys.pop(err_item['_id'])] = \
                            XsdString(err_item['error']['reason'])
                except KeyError:
                    error_bnodes[bonode_keys.pop(err_item['_id'])] = \
                            XsdString(err_item['error']['reason'])

        sparql_good = """
            DELETE
            {{
                ?s kds:esIndexTime ?esTime .
                ?s kds:esIndexError ?esError .
            }}
            INSERT
            {{
                ?s kds:esIndexTime {idx_time} .
            }}
            WHERE
            {{
                VALUES ?s {{ {subj_list} }} .
                OPTIONAL {{
                    ?s kds:esIndexTime ?esTime
                }}
                OPTIONAL {{
                    ?s kds:esIndexError ?esError
                }}
            }}
            """.format(idx_time=idx_time.sparql,
                       subj_list= "\n".join(uri_keys.values()))
        self.tstore_conn.update_query(sparql_good)
        # Process any errors that were found.
        if not error_dict:
            return
        sparql_error = """
            DELETE
            {{
                ?s kds:esIndexTime ?esTime .
                ?s kds:esIndexError ?esError .
            }}
            WHERE
            {{
                VALUES ?s {{ {subj_list} }} .
                OPTIONAL {{
                    ?s kds:esIndexTime ?esTime
                }}
                OPTIONAL {{
                    ?s kds:esIndexError ?esError
                }}
            }}
            """.format(subj_list= "\n".join(error_dict.keys()))
        self.tstore_conn.update_query(sparql_error)
        del sparql_error
        error_template = """
            {uri} kds:esIndexTime {idx_time} ;
                kds:esIndexError {reason} .
            """
        error_ttl = NSM.prefix("turtle") + \
                    "".join([error_template.format(idx_time=idx_time.sparql,
                                                   uri=key.sparql,
                                                   reason = value.sparql)
                             for key, value in error_dict.items()])
        self.tstore_conn.load_data(data=error_ttl, datatype='ttl')
