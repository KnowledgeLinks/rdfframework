__author__ = "Mike Stabile, Jeremy Nelson"
import time
import datetime
import inspect
import logging
import gc
import os
import pdb
import time
import threading
import copy
import json

from elasticsearch_dsl import Search

# logging.basicConfig(level=logging.DEBUG)
# lg_r = logging.getLogger("requests")
# lg_r.setLevel(logging.CRITICAL)

from elasticsearch_dsl import Search

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

    def __init__(self, rdf_class, tstore_conn, search_conn, **kwargs):
        log.setLevel(self.log_level)
        self.tstore_conn = tstore_conn
        self.search_conn = search_conn

        try:
            self.es_index = rdf_class.es_defs.get('kds_esIndex')[0]
            self.es_doc_type = rdf_class.es_defs.get('kds_esDocType')[0]
        except TypeError:
            log.warn("'%s' is NOT cofigured for indexing to elasticsearch",
                     rdf_class)
            return
        self.search = Search(using=search_conn.es).index(self.es_index)
        self.rdf_class = rdf_class
        self._set_es_workers(**kwargs)
        self.idx_start_time = XsdDatetime(datetime.datetime.utcnow())
        # add all of the sublcasses for a rdf_class
        self.rdf_types = [rdf_class.uri] + [item.uri
                                            for item in rdf_class.subclasses]
        # self.query = self.items_query_template.format(
        #         rdf_types="\n\t\t".join(rdf_types),
        #         idx_start_time=XsdDatetime(datetime.datetime.utcnow()).sparql)
        EsMappings().initialize_indices()
        if kwargs.get("reset_idx"):
            self.delete_idx_status(self.rdf_class)
        self.count = 0
        kwargs['uri_list'] = self.get_uri_list()
        # self._index_group_with_subgroup(**kwargs)
        while len(kwargs['uri_list']) > 0:
            self._index_group_with_subgroup(**kwargs)
            kwargs['uri_list'] = self.get_uri_list()

    def _set_es_workers(self, **kwargs):
        """
        Creates index worker instances for each class to index

        kwargs:
        -------
            idx_only_base[bool]: True will only index the base class
        """
        def make_es_worker(search_conn, es_index, es_doc_type, class_name):
            """
            Returns a new es_worker instance

            args:
            -----
                search_conn: the connection to elasticsearch
                es_index: the name of the elasticsearch index
                es_doc_type: the name of the elasticsearch doctype
                class_name: name of the rdf class that is being indexed
            """
            new_esbase = copy.copy(search_conn)
            new_esbase.es_index = es_index
            new_esbase.doc_type = es_doc_type
            log.info("Indexing '%s' into ES index '%s' doctype '%s'",
                     class_name.pyuri,
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
        if not kwargs.get("idx_only_base"):
            self.other_indexers = {item.__name__: make_es_worker(
                        self.search_conn,
                        item.es_defs.get('kds_esIndex')[0],
                        item.es_defs.get('kds_esDocType')[0],
                        item.__name__)
                    for item in additional_indexers(self.rdf_class)}
        else:
            self.other_indexers = {}

    def _index_sub(self, uri_list, num, batch_num):
        """
        Converts a list of uris to elasticsearch json objects

        args:
            uri_list: list of uris to convert
            num: the ending count within the batch
            batch_num: the batch number
        """
        bname = '%s-%s' % (batch_num, num)
        log.debug("batch_num '%s' starting es_json conversion",
                  bname)
        qry_data = get_all_item_data([item[0] for item in uri_list],
                                     self.tstore_conn,
                                     rdfclass=self.rdf_class)
        log.debug("batch_num '%s-%s' query_complete | count: %s",
                  batch_num,
                  num,
                  len(qry_data))
        # path = os.path.join(CFG.dirs.cache, "index_pre")
        # if not os.path.exists(path):
        #     os.makedirs(path)
        # with open(os.path.join(path, bname + ".json"), "w") as fo:
        #     fo.write(json.dumps(qry_data))
        data = RdfDataset(qry_data)
        del qry_data
        log.debug("batch_num '%s-%s' RdfDataset Loaded", batch_num, num)
        for value in uri_list:
            try:

                self.batch_data[batch_num]['main'].append(\
                        data[value[0]].es_json())
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

    def get_uri_list(self, **kwargs):
        """
        Returns a list of Uris to index
        """
        index_status_filter = """
                optional {{ ?s dcterm:modified ?modTime }} .
                optional {{ ?s kds:esIndexTime ?time }} .
                optional {{ ?s kds:esIndexError ?error }}
                filter (
                    !(bound(?time)) ||
                    ?time<?modTime  ||
                    (bound(?error) && ?time < {idx_start_time}))
                """.format(idx_start_time=self.idx_start_time.sparql)
        items_query_template = """
            SELECT DISTINCT ?s ?es_id
            {{
                VALUES ?rdftypes {{\n\t\t{rdf_types} }} .
                ?s a ?rdftypes .
                BIND(SHA1(STR(?s)) as ?es_id) .
                {status_filter}
            }}
            {order_by}
            """
        status_filter = index_status_filter \
                        if not kwargs.get("no_status") else ""
        order_by = kwargs.get("order_by", "")
        sparql = items_query_template.format(
                rdf_types="\n\t\t".join(self.rdf_types),
                status_filter=status_filter,
                order_by=order_by)
        results = [(Uri(item['s']['value']), item['es_id']['value'],)
                   for item in self.tstore_conn.query(sparql=sparql)]
        return results #[:100]

    def _index_group_with_subgroup(self, **kwargs):
        """ indexes all the URIs defined by the query into Elasticsearch """

        log.setLevel(self.log_level)
        # get a list of all the uri to index
        uri_list = kwargs.get('uri_list', self.get_uri_list())
        if not uri_list:
            log.info("0 items to index")
            return
        # results = results[:100]
        # Start processing through uri
        batch_file = os.path.join(CFG.dirs.logs, "batch_list.txt")
        # with open(batch_file, "w") as fo:
        #     fo.write("{")
        log.info("'%s' items to index", len(uri_list))
        self.time_start = datetime.datetime.now()
        batch_size = kwargs.get("batch_size", 12000)
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
                qry_size = kwargs.get("qry_size", 1000)
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
                    # with open(batch_file, "a") as fo:
                    #     fo.write(json.dumps({str('%s-%s' % (batch_num, i+1)):
                    #                          [item[0].sparql
                    #                           for item in sub_batch]})[1:-1]+",\n")
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
            try:
                del pyrdf.memorized
                pyrdf.memorized = {}
            except AttributeError:
                pass
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
            log.debug(datetime.datetime.now() - self.time_start)
        # with open(batch_file, 'rb+') as fo:
        #     fo.seek(-2, os.SEEK_END)
        #     fo.truncate()
        #     # fo.close()
        #     fo.write("}".encode())

    def _update_triplestore(self, es_result, action_list, **kwargs):
        """
        updates the triplestore with success of saves and failues of indexing

        Args:
        -----
            es_result: the elasticsearch result list
            action_list: list of elasticsearch action items that were indexed
        """
        idx_time = XsdDatetime(datetime.datetime.utcnow())
        uri_keys = {}
        bnode_keys = {}
        for item in action_list:
            try:
                uri_keys[item['_id']] = item['_source']["uri"]
            except KeyError:
                bnode_keys[item['_id']] = item['_id']
        error_dict = {}
        error_bnodes = {}
        if es_result[1]:
            for result in es_result[1]:
                err_item = list(result.values())[0]
                try:
                    error_dict[uri_keys.pop(err_item['_id'])] = \
                            XsdString(err_item['error']['reason'])
                except KeyError:
                    error_bnodes[bnode_keys.pop(err_item['_id'])] = \
                            XsdString(err_item['error']['reason'])
        if uri_keys:
            sparql_good = """
                DELETE
                {{
                    ?s kds:esIndexTime ?esTime .
                    ?s kds:esIndexError ?esError .
                }}
                INSERT
                {{
                    GRAPH ?g {{ ?s kds:esIndexTime {idx_time} }}.
                }}
                WHERE
                {{
                    VALUES ?s {{ {subj_list} }} .
                    {{
                        SELECT DISTINCT ?g ?s ?esTime ?esError
                        {{
                            GRAPH ?g {{ ?s ?p ?o }} .
                            OPTIONAL {{
                                ?s kds:esIndexTime ?esTime
                            }}
                            OPTIONAL {{
                                ?s kds:esIndexError ?esError
                            }}
                        }}
                    }}
                }}
                """.format(idx_time=idx_time.sparql,
                           subj_list="<%s>" % ">\n<".join(uri_keys.values()))
            self.tstore_conn.update_query(sparql_good)
        # Process any errors that were found.
        if not error_dict:
            return
        # Delete all indexing triples related to the error subjects
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
            """.format(subj_list="<%s>" % ">\n<".join(error_dict.keys()))
        self.tstore_conn.update_query(sparql_error)
        del sparql_error
        sparql_update = """
            INSERT
            {{
                GRAPH ?g {{
                    ?s kds:esIndexTime {idx_time} .
                    ?s kds:esIndexError ?esError .
                }}
            }}
            WHERE
            {{
                VALUES (?s ?esError) {{ {error_list} }} .
                {{
                    SELECT DISTINCT ?g ?s
                    {{
                        graph ?g {{?s ?p ?o}}
                    }}
                }}
            }}""".format(
                    idx_time=idx_time.sparql,
                    error_list="\n".join(["(<%s> %s)" % (key, val.sparql)
                                          for key, val in error_dict.items()]))

        # Create a turtle data stream of the new errors to upload into the
        # triplestore
        self.tstore_conn.update_query(sparql_update)
        del sparql_update


    def delete_idx_status(self, rdf_class):
        """
        Removes all of the index status triples from the datastore

        Args:
        -----
            rdf_class: The class of items to remove the status from
        """

        sparql_template = """
            DELETE
            {{
                ?s kds:esIndexTime ?esTime .
                ?s kds:esIndexError ?esError .
            }}
            WHERE
            {{

                VALUES ?rdftypes {{\n\t\t{} }} .
                ?s a ?rdftypes .
                OPTIONAL {{
                    ?s kds:esIndexTime ?esTime
                }}
                OPTIONAL {{
                    ?s kds:esIndexError ?esError
                }}
                FILTER(bound(?esTime)||bound(?esError))
            }}
            """
        rdf_types = [rdf_class.uri] + [item.uri
                                       for item in rdf_class.subclasses]
        sparql = sparql_template.format("\n\t\t".join(rdf_types))
        log.warn("Deleting index status for %s", rdf_class.uri)
        return self.tstore_conn.update_query(sparql)

    def get_es_ids(self):
        """
        reads all the elasticssearch ids for an index
        """
        search = self.search.source(['uri']).sort(['uri'])
        es_ids = [item.meta.id for item in search.scan()]
        return es_ids

    def validate_index(self, rdf_class):
        """
        Will compare the triplestore and elasticsearch index to ensure that
        that elasticsearch and triplestore items match. elasticsearch records
        that are not in the triplestore will be deleteed
        """
        es_ids = set(self.get_es_ids())
        tstore_ids = set([item[1]
                          for item in self.get_uri_list(no_status=True)])
        diff = es_ids - tstore_ids
        if diff:
            pdb.set_trace()
            action_list = self.es_worker.make_action_list(diff,
                                                          action_type="delete")
            results = self.es_worker.bulk_save(action_list)


