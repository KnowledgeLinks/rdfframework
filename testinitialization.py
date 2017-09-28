"""    This module is used for setting an intial test configs and values for
the rdfframework """

import sys
import os
import pdb
import pprint
import json
import types
import inspect
import logging
import requests
import datetime
from hashlib import sha1
PACKAGE_BASE = os.path.abspath(
    os.path.split(
        os.path.dirname(__file__))[0])
print("PACKAGE_BASE: ", PACKAGE_BASE)

from testconfig import config
from rdfframework.utilities import DictClass, pp, RdfNsManager, pp, \
                                   render_without_request, RdfConfigManager, \
                                   make_list, p_args, string_wrap, \
                                   make_doc_string, format_doc_vals, \
                                   list_files, iri
from rdfframework.triplestores import Blazegraph
from rdfframework.rdfdatatypes import rdfdatatypes as rdt, BaseRdfDataType, Uri
from rdfframework.sparql import run_sparql_query, correction_queries
from rdfframework.framework import RdfFramework
from rdfframework.rdfdatasets import RdfDataset
import rdfframework.rdfclass
from rdfframework.search import EsMappings, EsRdfBulkLoader, EsBase
from rdfframework.datamergers import *

r = rdfframework.rdfclass

try:
    MNAME = inspect.stack()[0][1]
except:
    MNAME = "testing"

CFG = RdfConfigManager(config=config)
pdb.set_trace()
NSM = RdfNsManager(config=CFG)
rdf_defs = CFG.RDF_DEFINITIONS
pyrdf = rdt.pyrdf
bg = Blazegraph()
# RdfFramework(reset=True)

rdfframework.rdfclass.RdfClassGenerator(reset=False)
# start = datetime.datetime.now()
# print("Start correction_queries: ", start)
# for qry in correction_queries:
#     result = run_sparql_query(qry, mode='update', namespace="kean_all")
# print("completed in: ", datetime.datetime.now() - start)

# start_time = datetime.datetime.now()
# print("Start topic_merger: ", )
# topic_merger = SparqlMerger(bg, GET_MERGE_URIS, namespace="kean_marc")
# topic_merger.run()
# print("completed in: ", datetime.datetime.now() - start)

# e = EsMappings()
# print(e.list_mapped_classes())
# e.initialize_indices(action="update")

# start_time = datetime.datetime.now()
# print("Start work index: ", )
# EsRdfBulkLoader(r.bf_Work, 'kean_marc')
# print("completed in: ", datetime.datetime.now() - start)


# work_sparql = "SELECT ?item { ?item a bf:Work } limit 1000"

# work_list = run_sparql_query(work_sparql, namespace="kean_all")
# work_list = ["BIND(<%s> as ?item) ." % item['item']['value'] \
#              for item in work_list]
# statement = "{\n%s\n}" % "\n} UNION {\n".join(work_list)

# bulk_sparql = render_without_request("sparqlAllItemDataTemplate_Bulk.rq",
#                                 bulk_list=statement,
#                                 prefix=NSM.prefix())
# start = datetime.datetime.now()
# z = run_sparql_query(bulk_sparql, namespace="kean_all")
# print("query time: ", datetime.datetime.now()-start)
# start2 = datetime.datetime.now()
# b = RdfDataset(z)
# print("py_dataset_load", datetime.datetime.now() - start2)
# print("total time: ", datetime.datetime.now() - start)
sparql = render_without_request("sparqlAllItemDataTemplate.rq",
                                item_uri="<http://library.kean.edu/206605#Work>",
                                prefix=NSM.prefix())
kean_conn = Blazegraph(namespace="kean_all")
x = kean_conn.query(sparql)
# x = run_sparql_query(sparql, namespace="kean_all")
#pp.pprint([pyrdf(item['kdsClass']) for item in x])

y = RdfDataset(x, "<http://library.kean.edu/206605#Work>")



sparql2 = render_without_request("sparqlAllItemDataTemplate.rq",
        item_uri="<http://id.loc.gov/authorities/subjects/sh85055163>",
        prefix=NSM.prefix())
lr = kean_conn.query(sparql2)
#pp.pprint([pyrdf(item['kdsClass']) for item in x])

l = RdfDataset(lr,
               "<http://id.loc.gov/authorities/subjects/sh85055163>",
               debug=True)
# print(json.dumps(l.base_class.es_json(),indent=4))

# EsRdfBulkLoader(r.bf_Topic)

# logging.basicConfig(level=logging.DEBUG)
# lg = logging.getLogger("%s.%s" % ('locsubject_load', inspect.stack()[0][3]))
# lg.setLevel(logging.DEBUG)


# stmt = "DROP GRAPH %s;" % CFG.RDF_LOC_SUBJECT_GRAPH
# drop_extensions = requests.post(
#     url=CFG.TRIPLESTORE_URL,
#     params={"update": stmt})
# lg.info("loading Loc Subjects graph to the triplestore")
# # load the subjects graph to the db
# data = "file:///local_data/%s" % 'loc_subjects_skos.nt.gz'
# result = requests.post(
#         url=CFG.TRIPLESTORE_URL,
#         params={"context-uri": CFG.RDF_LOC_SUBJECT_GRAPH,
#                 "uri": data})
# lg.info("loc subjects loaded")

# sparql = render_without_request("sparqlClassDefinitionList.rq",
#                                  graph=CFG.RDF_DEFINITION_GRAPH,
#                                  prefix=NSM.prefix())
# x = run_sparql_query(sparql, namespace=CFG.RDF_DEFINITIONS.namespace)
# #pp.pprint([pyrdf(item['kdsClass']) for item in x])
# _sparql = render_without_request("sparqlClassDefinitionDataTemplate.rq",
#                                  prefix=NSM.prefix(),
#                                  item_uri="bf:Topic",
#                                  graph=CFG.RDF_DEFINITION_GRAPH)
# z = run_sparql_query(_sparql, namespace=rdf_defs.namespace)

# sparqldefs = render_without_request("sparqlAllRDFClassDefs.rq",
#                                  graph=CFG.RDF_DEFINITION_GRAPH,
#                                  prefix=NSM.prefix())
# # print(sparqldefs)
# y = run_sparql_query(sparqldefs, namespace=rdf_defs.namespace)

# # h = RdfDataset
# # def group_classess(data, group_key="kdsClass"):
# #     rtn_obj = {}
# #     for row in data:
# #         try:
# #             rtn_obj[.append(row)
# ds = RdfDataset()
# ds.load_data(z, strip_orphans=True, obj_method="list")
# # ds.classes
# #print(json.dumps(ds, indent=4))
