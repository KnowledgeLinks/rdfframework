"""	This module is used for setting an intial test configs and values for 
the rdfframework """

import sys
import os

PACKAGE_BASE = os.path.abspath(
    os.path.split(
        os.path.dirname(__file__))[0])
print("PACKAGE_BASE: ", PACKAGE_BASE)
sys.path.append(PACKAGE_BASE)

from testconfig import config

from rdfframework.getframework import fw_config as fwc, get_framework as fw
from rdfframework.utilities import DictClass, pp, RdfNsManager, \
								   render_without_request, RdfConfigManager
from rdfframework.rdfdatatypes import rdfdatatypes as rdt
from rdfframework.sparql import run_sparql_query
print("CONFIG ---------------------------------------------------------------")
#config = DictClass(config)
pp.pprint(config)
print("----------------------------------------------------------------------")
#fw(config=config, root_file_path=PACKAGE_BASE)
#NSM = get_ns_obj(config=DictClass(config))
config2 = RdfConfigManager(config=config)
NSM = RdfNsManager(config=config2)
rdf_defs = config2.RDF_DEFINITIONS

sparql = render_without_request("sparqlClassDefinitionList.rq",
                                             graph=rdf_defs.graph,
                                             prefix=NSM.prefix())
print(sparql)
x = run_sparql_query(sparql, namespace=config2.RDF_DEFINITIONS.namespace)
y = [rdt.pyrdf(i['kdsClass']) for i in x]

_sparql = render_without_request("sparqlClassDefinitionDataTemplate.rq",
                                 prefix=NSM.prefix(),
                                 item_uri=y[0].sparql,
                                 graph=rdf_defs.graph)
z = run_sparql_query(_sparql, namespace=rdf_defs.namespace)

#class_uri = z[0]
# sparql = render_without_request("sparqlClassDefinitionDataTemplate.rq",
#                                 prefix=NSM.prefix(),
#                                 item_uri=class_uri,
#                                 graph=config2.RDF_DEFINITIONS.namespace)