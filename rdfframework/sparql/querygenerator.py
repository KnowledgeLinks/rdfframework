import os
import requests
import copy
import json
import pdb


from rdfframework.utilities import render_without_request
from rdfframework.datatypes import RdfNsManager, Uri

NSM = RdfNsManager()
DEBUG = True

def get_all_item_data(item_uri, conn, graph=None, output='json', **kwargs):
    if output == 'json':
        sparql = render_without_request("sparqlAllItemDataTemplate.rq",
                                        prefix=NSM.prefix(),
                                        item_uri=Uri(item_uri).sparql)
        # print(sparql)
        return conn.query(sparql)
    elif output == 'rdf':
        sparql = render_without_request("sparqlAllItemDataTemplateConstruct.rq",
                                        prefix=NSM.prefix(),
                                        item_uri=Uri(item_uri).sparql)
        # print(sparql)
        return conn.query(sparql, rtn_format='rdf', **kwargs)

def get_graph(graph, conn, **kwargs):
    sparql = render_without_request("sparqlGraphDataTemplate.rq",
                                    prefix=NSM.prefix(),
                                    graph=graph)
    return conn.query(sparql, **kwargs)
