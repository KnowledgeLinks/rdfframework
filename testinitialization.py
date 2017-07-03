"""    This module is used for setting an intial test configs and values for 
the rdfframework """

import sys
import os
import pdb
import pprint
import json

PACKAGE_BASE = os.path.abspath(
    os.path.split(
        os.path.dirname(__file__))[0])
print("PACKAGE_BASE: ", PACKAGE_BASE)
sys.path.append(PACKAGE_BASE)

from testconfig import config
from rdfframework.utilities import DictClass, pp, RdfNsManager, pp, \
                                   render_without_request, RdfConfigManager, \
                                   make_list
from rdfframework.rdfdatatypes import rdfdatatypes as rdt
from rdfframework.sparql import run_sparql_query
from rdfframework.framework import RdfFramework
from rdfframework.rdfdatasets import RdfDataset

print("CONFIG ---------------------------------------------------------------")
#config = DictClass(config)
pp.pprint(config)
print("----------------------------------------------------------------------")
CFG = RdfConfigManager(config=config)
NSM = RdfNsManager(config=CFG)
rdf_defs = CFG.RDF_DEFINITIONS
pyrdf = rdt.pyrdf
sparql = render_without_request("sparqlClassDefinitionList.rq",
                                 graph=CFG.RDF_DEFINITION_GRAPH,
                                 prefix=NSM.prefix())
x = run_sparql_query(sparql, namespace=CFG.RDF_DEFINITIONS.namespace)
#pp.pprint([pyrdf(item['kdsClass']) for item in x])
_sparql = render_without_request("sparqlClassDefinitionDataTemplate.rq",
                                 prefix=NSM.prefix(),
                                 item_uri="bf:Topic",
                                 graph=CFG.RDF_DEFINITION_GRAPH)
z = run_sparql_query(_sparql, namespace=rdf_defs.namespace)





ds = RdfDataset()
ds.load_data(z, strip_orphans=True, obj_method="list")
ds.classes
#print(json.dumps(ds, indent=4))
RdfFramework(reset=True)