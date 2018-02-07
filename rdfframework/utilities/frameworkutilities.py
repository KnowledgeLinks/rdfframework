"""frameworkutilities.py

Module of helper functions used in the RDF Framework.

"""
__author__ = "Mike Stabile, Jeremy Nelson"

import copy
import pdb
import logging
import inspect
import json

from uuid import uuid1, uuid4, uuid5
from hashlib import sha1


#import rdfframework.rdfdatatypes as dt

xsd_to_python = "depricated"

MNAME = inspect.stack()[0][1]

DEBUG = True


class RdfJsonEncoder(json.JSONEncoder):
    # def __init__(self, *args, **kwargs):
    #     if kwargs.get("uri_format"):
    #         self.uri_format = kwargs.pop("uri_format")
    #     else:
    #         self.uri_format = 'sparql_uri'
    #     super(RdfJsonEncoder, self).__init__(*args, **kwargs)
    uri_format = 'sparql_uri'

    def default(self, obj):
        if isinstance(obj, RdfBaseClass):
            obj.uri_format = self.uri_format
            temp = obj.conv_json(self.uri_format)
            return temp
        elif isinstance(obj, RdfDataset):
            return obj._format(self.uri_format)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

def uid_to_repo_uri(id_value, url):
    if id_value:
        _uri = "{}/{}/{}/{}/{}/{}".format(url,
                                          id_value[:2],
                                          id_value[2:4],
                                          id_value[4:6],
                                          id_value[6:8],
                                          id_value)
        return _uri

class DataStatus(object):
    """ Checks and updates the data status from the triplestore

    args:
        group: the datagroup for statuses
    """
    ln = "%s-DataStatus" % MNAME
    log_level = logging.DEBUG


    def __init__(self, group, conn, **kwargs):

        self.group = group
        self.conn = conn

    def get(self, status_item):
        """ queries the database and returns that status of the item.

        args:
            status_item: the name of the item to check
        """
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)

        sparql = '''
            SELECT ?loaded
            WHERE {{
                kdr:{0} kds:{1} ?loaded .
            }}'''
        value = self.conn.query(sparql=sparql.format(self.group, status_item))
        if len(value) > 0 and \
                cbool(value[0].get('loaded',{}).get("value",False)):
            return True
        else:
            return False

    def set(self, status_item, status):
        """ sets the status item to the passed in paramaters

        args:
            status_item: the name if the item to set
            status: boolean value to set the item
        """
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        sparql = '''
            DELETE {{
                kdr:{0} kds:{1} ?o
            }}
            INSERT {{
                kdr:{0} kds:{1} "{2}"^^xsd:boolean
            }}
            WHERE {{
                OPTIONAL {{ kdr:{0} kds:{1} ?o }}
            }}'''
        return self.conn.query(sparql=sparql.format(self.group,
                                                     status_item,
                                                     str(status).lower()),
                                mode='update')


def new_id(method="uuid"):
    """ Generates a unique identifier to be used with any dataset. The
        default method will use a random generated uuid based on computer
        and a random generated uuid.

        Args:
            method: "uuid" -> default random uuid generation
                    ???? -> other methods can be added later
    """
    if method == "uuid":
        return str(uuid5(uuid1(),str(uuid4())).hex)


