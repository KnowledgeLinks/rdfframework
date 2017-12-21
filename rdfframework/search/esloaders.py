__author__ = "Mike Stabile, Jeremy Nelson"

import datetime
import inspect
import logging
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
from rdfframework.datatypes import RdfNsManager

CFG = RdfConfigManager()
NSM = RdfNsManager()

class EsRdfBulkLoader(object):
    """ Bulk loads data from the triplestore to elasticsearch """

    ln = "%s-EsRdfBulkLoader" % MNAME
    log_level = logging.DEBUG

    def __init__(self, rdf_class, namespace, conn):
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        lg.debug(" *** Started")
        self.conn = conn
        self.namespace = namespace
        self.es_index = rdf_class.es_defs.get('kds_esIndex')[0]
        self.es_doc_type = rdf_class.es_defs.get('kds_esDocType')[0]
        self.es_worker = EsBase(es_index=self.es_index,
                                doc_type=self.es_doc_type)
        self.rdf_class = rdf_class
        self.query = """
            SELECT DISTINCT ?s {{ ?s a {}. }}""".format(rdf_class.uri)
        EsMappings().initialize_indices()
        self.count = 0
        self._index_group_with_subgroup()

    def _index_item(self, uri, num, batch_num):
        """ queries the triplestore for an item sends it to elasticsearch """

        data = RdfDataset(get_all_item_data(uri, self.conn),
                          uri).base_class.es_json()
        self.batch_data[batch_num].append(data)
        self.count += 1


    def _index_group(self):
        """ indexes all the URIs defined by the query into Elasticsearch """

        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        # get a list of all the uri to index
        results = self.conn.query(sparql=self.query, namespace=self.namespace)
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
            lg.debug("batch %s: %s-%s", batch_num, batch_start, batch_end)
            for i, subj in enumerate(results[batch_start:batch_end]):
                th = threading.Thread(name=batch_start + i + 1,
                                      target=self._index_item,
                                      args=(MSN.iri(subj['s']['value']),
                                            i+1,batch_num,))
                th.start()
            lg.debug(datetime.datetime.now() - self.time_start)
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
            lg.debug(datetime.datetime.now() - self.time_start)

    def _index_sub(self, uri_list, num, batch_num):

        def run_query(uri_list):
            item_list = ["BIND(<%s> as ?item) ." % item['s']['value'] \
                         for item in uri_list]
            statement = "{\n%s\n}" % "\n} UNION {\n".join(item_list)
            bulk_sparql = render_without_request(\
                                "sparqlAllItemDataTemplate_Bulk.rq",
                                bulk_list=statement,
                                prefix=NSM.prefix())
            return self.conn.query(bulk_sparql, namespace=self.namespace)

        data = RdfDataset(run_query(uri_list))
        for value in data.values():
            if isinstance(value, self.rdf_class):
                self.batch_data[batch_num].append(value.es_json())
                self.count += 1

    def _index_group_with_subgroup(self):
        """ indexes all the URIs defined by the query into Elasticsearch """

        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        # get a list of all the uri to index
        results = self.conn.query(sparql=self.query, namespace=self.namespace)
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
            lg.debug("batch %s: %s-%s", batch_num, batch_start, batch_end)
            sub_batch = []
            j = 0
            for i, subj in enumerate(results[batch_start:batch_end]):
                qry_size = 1000
                if j < qry_size:
                    sub_batch.append(subj)
                if j == qry_size -1 or i == batch_end - 1:
                    # pdb.set_trace()
                    sub_batch.append(subj)
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
            lg.debug(datetime.datetime.now() - self.time_start)
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
            lg.debug(datetime.datetime.now() - self.time_start)
