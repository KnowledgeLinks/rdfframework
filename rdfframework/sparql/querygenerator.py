import os
import requests
import copy
import json
import pdb


from rdfframework.utilities import render_without_request
from rdfframework.datatypes import RdfNsManager

NSM = RdfNsManager()
DEBUG = True

def get_all_item_data(item_uri, conn, graph=None):
    sparql = render_without_request("sparqlAllItemDataTemplate.rq",
                                    prefix=NSM.prefix(),
                                    item_uri=item_uri)
    return conn.query(sparql)

def get_graph(graph, conn):
    sparql = render_without_request("sparqlGraphDataTemplate.rq",
                                    prefix=NSM.prefix(),
                                    graph=graph)
    return conn.query(sparql)
