import os
import requests
import copy
import json
import pdb


from rdfframework.utilities import render_without_request
from rdfframework.configuration import RdfNsManager

NSM = RdfNsManager()
DEBUG = True

def get_all_item_data(item_uri, conn):
    ns = NSM
    _sparql = render_without_request("sparqlAllItemDataTemplate.rq",
                                     prefix=ns.prefix(),
                                     item_uri=item_uri)
    return conn.query(_sparql)
