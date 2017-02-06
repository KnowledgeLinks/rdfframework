''' contains functions for converting objects to namespace prefixes '''
import re
import inspect
import logging
import pdb

from rdflib import Namespace, Graph, URIRef
from rdflib.namespace import NamespaceManager
from rdfframework.utilities import get_ns_obj

__author__ = "Mike Stabile, Jeremy Nelson"

NS_OBJ = None
NS_GRAPH = Graph()
DEBUG = True
# set the modulename
MNAME = inspect.stack()[0][1]

def convert_to_ns(value, ns_obj=None, rdflib_uri=False):
    ''' converts a value to the prefixed rdf ns equivalent. If not found
        returns the value as is '''
    ns_obj = get_ns_obj(ns_obj)
    for _prefix, _ns_uri in ns_obj.namespaces():
        if str(value).startswith(_prefix + ":") or \
                str(value).startswith("<%s:" % _prefix):
            return value.replace(_prefix + ":", _prefix + "_").replace(\
                    "<","").replace(">","")
        if str(value).startswith(str(_ns_uri)) or str(value).startswith("<"+str(_ns_uri)):
            return value.replace(str(_ns_uri), _prefix + "_").replace(\
                    "<","").replace(">","")
    return value

def convert_to_ttl(value, ns_obj=None):
    ''' converts a value to the prefixed rdf ns equivalent. If not found
        returns the value as is '''
    ns_obj = get_ns_obj(ns_obj)
    for _prefix, _ns_uri in ns_obj.namespaces():
        _ns_uri = str(_ns_uri)
        if str(value).startswith(_prefix + "_") or \
                str(value).startswith("<%s_" % _prefix):
            return value.replace(_prefix + "_", _prefix + ":").replace(\
                    "<","").replace(">","")
        if str(value).startswith(_ns_uri) or str(value).startswith("<"+_ns_uri):
            return value.replace(_ns_uri, _prefix + ":").replace(\
                    "<","").replace(">","")
    return iri(value)

def convert_to_uri(value, ns_obj=None, strip_iri=False, rdflib_uri=False):
    ''' converts a prefixed rdf ns equivalent value to its uri form.
        If not found returns the value as is 

        args:
            value: the URI/IRI to convert
            strip_iri: removes the < and > signs
            rdflib_uri: returns an rdflib URIRef
    '''

    ns_obj = get_ns_obj(ns_obj)
    value = str(value).replace("<","").replace(">","")
    for _prefix, _ns_uri in ns_obj.namespaces():
        if str(value).startswith(_prefix + "_") or \
                str(value).startswith("<%s_" % _prefix):
            #pdb.set_trace()
            if strip_iri or rdflib_uri:
                return_val = value.replace("%s_" % _prefix, str(_ns_uri)).replace(\
                        "<","").replace(">","")
                if rdflib_uri:
                    return_val = URIRef(return_val)
                return return_val
            else:
                return iri(value.replace("%s_" % _prefix, str(_ns_uri)))
        if str(value).startswith(_prefix + ":") or \
                str(value).startswith("<%s:" % _prefix):
            #pdb.set_trace()
            if strip_iri or rdflib_uri:
                return_val = value.replace("%s:" % _prefix, str(_ns_uri)).replace(\
                        "<","").replace(">","")
                #pdb.set_trace()
                if rdflib_uri:
                    return_val = URIRef(return_val)
                return return_val
            else:
                return iri(value.replace("%s:" % _prefix, str(_ns_uri)))
    if str(value).lower() == "none":
        return ""
    else:
        if rdflib_uri:
            URIRef(value)
        elif strip_iri:
            return value
        else:
            return iri(value)

def convert_obj_to_rdf_namespace(obj, 
                                 ns_obj=None, 
                                 key_only=False,
                                 rdflib_uri=False):
    """This function takes rdf json definitions and converts all of the
        uri strings to a ns_value format_

        args:
            obj: the dictionary object to convert
            ns_obj: RdfNsManager instance *optional
            key_only: Default = False, True = convert only the dictionary keys
    """
    if not ns_obj:
        ns_obj = get_ns_obj(ns_obj)

    if isinstance(obj, list):
        _return_list = []
        for item in obj:
            if isinstance(item, list):
                _return_list.append(convert_obj_to_rdf_namespace(item, 
                                                                 ns_obj,
                                                                 key_only,
                                                                 rdflib_uri))
            elif isinstance(item, dict):
                _return_list.append(convert_obj_to_rdf_namespace(item,
                                                                 ns_obj,
                                                                 key_only,
                                                                 rdflib_uri))
            else:
                if key_only:
                    if rdflib_uri:
                        #pdb.set_trace()
                        _return_list.append(convert_to_uri(item, 
                                                           rdflib_uri=True))
                    else:
                        _return_list.append(item)
                else:
                    _return_list.append(convert_to_ns(item, ns_obj))
        return _return_list
    elif isinstance(obj, dict):
        _return_obj = {}
        for key, item in obj.items():
            nkey = convert_to_ns(key, ns_obj)
            if isinstance(item, list):
                _return_obj[nkey] = convert_obj_to_rdf_namespace(item,
                                                                 ns_obj,
                                                                 key_only,
                                                                 rdflib_uri)
            elif isinstance(item, dict):
                _return_obj[nkey] = convert_obj_to_rdf_namespace(item,
                                                                 ns_obj,
                                                                 key_only,
                                                                 rdflib_uri)
            else:
                if key_only:
                    #pdb.set_trace()
                    if rdflib_uri:
                        _return_obj[nkey] = convert_to_uri(item, 
                                                           rdflib_uri=True)
                    else:
                        _return_obj[nkey] = item
                else:
                    _return_obj[nkey] = convert_to_ns(item, ns_obj, rdflib_uri)
        return _return_obj
    else:
        if key_only: 
            if rdflib_uri:
                #pdb.set_trace()
                return convert_to_uri(item, rdflib_uri=True)
            else:
                return obj
        else:
            return convert_to_ns(obj, ns_obj, rdflib_uri)

def pyuri(value):
    ''' converts an iri to the app defined rdf namespaces in the framework
        in a python accessable format. i.e. schema:name or
        http:schema.org/name  --> schema_name '''
    ns_obj = get_ns_obj()
    if str(value).startswith("http"):
        return convert_to_ns(value, ns_obj)
    else:
        return convert_to_ns(convert_to_uri(value, ns_obj), ns_obj)

def ttluri(value):
    ''' converts an iri to the app defined rdf namespaces in the framework
        in a turtle accessable format. i.e. schema_name or
        http:schema.org/name  --> schema:name '''
    ns_obj = get_ns_obj()
    if str(value).startswith("http"):
        return convert_to_ttl(value, ns_obj)
    else:
        return convert_to_ttl(convert_to_uri(value, ns_obj), ns_obj)

def nouri(value):
    """ removes all of the namespace portion of the uri 
    i.e. http://www.schema.org/name  becomes name

    Args:
        value: the uri to convert
    Returns:
        stripped value from namespace
    """
    ns_obj = get_ns_obj()
    _uri = None
    if not clean_iri(str(value)).startswith("http"):
        _uri = convert_to_uri(value, ns_obj)
    else:
        _uri = value
    if _uri:
        return re.sub(r"^(.*[#/])", "", str(_uri))
    else:
        return value

def uri_prefix(value):
    ''' Takes a uri and returns the prefix for that uri '''
    if not DEBUG:
        debug = False
    else:
        debug = False
    if debug: print("START uri_prefix() uriconvertor.py -------------------\n")
    ns_obj = get_ns_obj()
    _uri = None
    if not clean_iri(str(value)).startswith("http"):
        _uri = convert_to_uri(str(value), NS_OBJ)
    else:
        _uri = str(value)
    _ns_uri = _uri.replace(re.sub(r"^(.*[#/])", "", str(_uri)),"")
    if debug: print("_uri: ", _uri)
    if debug: print("_ns_uri: ", _ns_uri)
    if _uri:
        for prefix, uri in NS_OBJ.namespaces():
            if debug: print("uri: ", uri, " prefix: ", prefix)
            if _ns_uri == str(uri):
                value = prefix
                break
    if debug: print("END uri_prefix() uriconvertor.py -------------------\n")
    return value

def uri(value, strip_iri=False, ns_obj=None):
    """ Converts py_uri or ttl uri to a http://... full uri format 

    Args:
        value: the string to convert

    Returns:
        full uri of an abbreivated uri
    """
    if not ns_obj:
        ns_obj = get_ns_obj()
    if clean_iri(str(value)).startswith("http"):
        return value
    else:
        return convert_to_uri(value, strip_iri=strip_iri, ns_obj=ns_obj)

def iris_to_strings(obj, ns_obj=None):
    ns_obj = get_ns_obj(ns_obj)

    if isinstance(obj, list):
        _return_list = []
        for item in obj:
            if isinstance(item, list):
                _return_list.append(iris_to_strings(item, ns_obj))
            elif isinstance(item, dict):
                _return_list.append(iris_to_strings(item, ns_obj))
            else:
                 _return_list.append(convert_to_uri(item, ns_obj, True))
        return _return_list
    elif isinstance(obj, dict):
        _return_obj = {}
        for key, item in obj.items():
            nkey = convert_to_ns(key, ns_obj)
            if isinstance(item, list):
                _return_obj[nkey] = iris_to_strings(item, ns_obj)
            elif isinstance(item, dict):
                _return_obj[nkey] = iris_to_strings(item, ns_obj)
            else:
                _return_obj[nkey] = convert_to_uri(item, ns_obj, True)
        return _return_obj
    else:
        return convert_to_uri(obj, ns_obj, True)

def clean_iri(uri_string):
    '''removes the <> signs from a string start and end'''
    uri_string = str(uri_string)
    if isinstance(uri_string, str):
        uri_string = uri_string.strip()
        if uri_string[:1] == "<" and uri_string[len(uri_string)-1:] == ">":
            uri_string = uri_string[1:len(uri_string)-1]
    return uri_string

def iri(uri_string):
    """converts a string to an IRI or returns an IRI if already formated

    Args:
        uri_string: uri in string format

    Returns:
        formated uri with <>
    """
    uri_string = str(uri_string)
    if uri_string[:1] == "?":
        return uri_string
    if uri_string[:1] == "[":
        return uri_string
    if uri_string[:1] != "<":
        uri_string = "<{}".format(uri_string.strip())
    if uri_string[len(uri_string)-1:] != ">":
        uri_string = "{}>".format(uri_string.strip())
    return uri_string

