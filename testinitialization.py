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
from hashlib import sha1
PACKAGE_BASE = os.path.abspath(
    os.path.split(
        os.path.dirname(__file__))[0])
print("PACKAGE_BASE: ", PACKAGE_BASE)
sys.path.append(PACKAGE_BASE)
from testconfig import config
from rdfframework.utilities import DictClass, pp, RdfNsManager, pp, \
                                   render_without_request, RdfConfigManager, \
                                   make_list, p_args, string_wrap, \
                                   make_doc_string, format_doc_vals, \
                                   list_files
from rdfframework.rdfdatatypes import rdfdatatypes as rdt, BaseRdfDataType, Uri
from rdfframework.sparql import run_sparql_query
from rdfframework.framework import RdfFramework
from rdfframework.rdfdatasets import RdfDataset
import rdfframework.rdfclass
from rdfframework.search import EsMappings, EsRdfBulkLoader
r = rdfframework.rdfclass

try:
    MNAME = inspect.stack()[0][1]
except:
    MNAME = "testing"

CFG = RdfConfigManager(config=config)
NSM = RdfNsManager(config=CFG)
rdf_defs = CFG.RDF_DEFINITIONS
pyrdf = rdt.pyrdf
# RdfFramework(reset=True)

rdfframework.rdfclass.RdfClassGenerator(reset=False)

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

from rdfframework.search import EsMappings as m
print(m.list_mapped_classes())

# e = EsMappings()
# e.initialize_indices(action="reset")

sparql = render_without_request("sparqlAllItemDataTemplate.rq",
                                item_uri="<http://library.kean.edu/10#Work>",
                                prefix=NSM.prefix())
x = run_sparql_query(sparql, namespace="kean_marc")
#pp.pprint([pyrdf(item['kdsClass']) for item in x])

y = RdfDataset(x, "<http://library.kean.edu/10#Work>")



sparql2 = render_without_request("sparqlAllItemDataTemplate.rq",
        item_uri="<http://id.loc.gov/authorities/subjects/sh85055163>",
        prefix=NSM.prefix())
lr = run_sparql_query(sparql2)
#pp.pprint([pyrdf(item['kdsClass']) for item in x])

l = RdfDataset(lr, 
               "<http://id.loc.gov/authorities/subjects/sh85055163>", 
               debug=True)
print(json.dumps(l.base_class.es_json(),indent=4))

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

