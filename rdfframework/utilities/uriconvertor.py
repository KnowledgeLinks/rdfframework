''' contains functions for converting objects to namespace prefixes '''
import re
import inspect
import logging

from rdflib import Namespace, Graph
from rdflib.namespace import NamespaceManager

__author__ = "Mike Stabile, Jeremy Nelson"

NS_OBJ = None
NS_GRAPH = Graph()
DEBUG = True
# set the modulename
MNAME = inspect.stack()[0][1]

def convert_to_ns(value, ns_obj=None):
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
    return value

def convert_to_uri(value, ns_obj=None, strip_iri=False):
    ''' converts a prefixed rdf ns equivalent value to its uri form.
        If not found returns the value as is '''

    ns_obj = get_ns_obj(ns_obj)
    for _prefix, _ns_uri in ns_obj.namespaces():
        if str(value).startswith(_prefix + "_") or \
                str(value).startswith("<%s_" % _prefix):
            if strip_iri:
                return value.replace("%s_" % _prefix, str(_ns_uri)).replace(\
                        "<","").replace(">","")
            else:
                return value.replace("%s_" % _prefix, str(_ns_uri))
        if str(value).startswith(_prefix + ":") or \
                str(value).startswith("<%s:" % _prefix):
            if strip_iri:
                return value.replace("%s:" % _prefix, str(_ns_uri)).replace(\
                        "<","").replace(">","")
            else:
                return value.replace("%s:" % _prefix, str(_ns_uri))
    if str(value).lower() == "none":
        return ""
    else:
        return value

def create_namespace_obj(obj):
    ''' takes initial rdf application definitions and reads the namespaces '''
    global NS_OBJ
    _ns_obj = {}
    # find the section of the obj that holds the all the namespaces
    _key_string = "http://knowledgelinks.io/ns/data-structures/appNameSpace"
    for _app_section in obj.values():
        try:
            for _section_key in _app_section.keys():
                if _section_key == _key_string:
                    _ns_obj = _app_section[_section_key]
                    break
        except AttributeError:
            pass
    return_obj = RdfNsManager()
    # cylce through the namespace section and add to the return obj
    for _ns in _ns_obj:
        _prefix_key = "http://knowledgelinks.io/ns/data-structures/prefix"
        _ns_key = 'http://knowledgelinks.io/ns/data-structures/nameSpaceUri'
        return_obj.bind(_ns.get(_prefix_key), Namespace(_ns.get(_ns_key)))
    NS_OBJ = return_obj
    return return_obj

def convert_obj_to_rdf_namespace(obj, ns_obj=None, key_only=False):
    """This function takes rdf json definitions and converts all of the
        uri strings to a ns_value format_

    args:
        obj: the dictionary object to convert
        ns_obj: RdfNsManager instance *optional
        key_only: Default = False, True = convert only the dictionary keys
    """
    ns_obj = get_ns_obj(ns_obj)

    if isinstance(obj, list):
        _return_list = []
        for item in obj:
            if isinstance(item, list):
                _return_list.append(convert_obj_to_rdf_namespace(item, 
                                                                 ns_obj,
                                                                 key_only))
            elif isinstance(item, dict):
                _return_list.append(convert_obj_to_rdf_namespace(item,
                                                                 ns_obj,
                                                                 key_only))
            else:
                if key_only:
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
                                                                 key_only)
            elif isinstance(item, dict):
                _return_obj[nkey] = convert_obj_to_rdf_namespace(item,
                                                                 ns_obj,
                                                                 key_only)
            else:
                if key_only:
                    _return_obj[nkey] = item
                else:
                    _return_obj[nkey] = convert_to_ns(item, ns_obj)
        return _return_obj
    else:
        if key_only:
            return obj
        else:
            return convert_to_ns(obj, ns_obj)

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
    ns_obj = get_ns_obj()
    _uri = None
    if not str(value).startswith("http"):
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
    if not str(value).startswith("http"):
        _uri = convert_to_uri(value, NS_OBJ)
    else:
        _uri = value
    _ns_uri = _uri.replace(re.sub(r"^(.*[#/])", "", str(_uri)),"")
    if debug: print("_uri: ", _uri)
    if debug: print("_ns_uri: ", _ns_uri)
    if _uri:
        for prefix, uri in NS_OBJ.namespaces():
            if debug: print("uri: ", uri, " prefix: ", prefix)
            if _ns_uri == uri:
                value = prefix
                break
    if debug: print("END uri_prefix() uriconvertor.py -------------------\n")
    return value

def uri(value):
    ns_obj = get_ns_obj()
    if str(value).startswith("http"):
        return value
    else:
        return convert_to_uri(value)

def get_ns_obj(ns_obj=None):
    """ returns an instance of the RdfNsManager

    Args:
        ns_obj: an RdfNsManager instance or None
    """
    global NS_OBJ
    if ns_obj is None and NS_OBJ is None:
        try:
            from rdfframework import get_framework
            ns_obj = get_framework().ns_obj
            if ns_obj is None:
                ns_obj = RdfNsManager()
                NS_OBJ = ns_obj
        except:
            if isinstance(NS_OBJ, RdfNsManager):
                ns_obj = NS_OBJ
            else:
                ns_obj = RdfNsManager()
                NS_OBJ = ns_obj
    else:
        ns_obj = NS_OBJ
    return ns_obj

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

    if uri_string[:1] == "?":
        return uri_string
    if uri_string[:1] == "[":
        return uri_string
    if uri_string[:1] != "<":
        uri_string = "<{}".format(uri_string.strip())
    if uri_string[len(uri_string)-1:] != ">":
        uri_string = "{}>".format(uri_string.strip())
    return uri_string

class RdfNsManager(NamespaceManager):
    """ Extends the the rdflib Namespace Manager. Provides additional methods
    to easily generate prefixes in use thoughout the application """
    ln = "%s-RdfNsManager" % MNAME
    log_level = logging.CRITICAL

    def __init__(self, *args, **kwargs):
        global NS_GRAPH
        graph = NS_GRAPH
        config = None
        if kwargs.get("config"):
            config = kwargs.pop("config")
        super(RdfNsManager, self).__init__(graph, *args, **kwargs)
        # load default ns's from config info
        
        if config and hasattr(config, "DEFAULT_RDF_NS"):
            self.dict_load(config.DEFAULT_RDF_NS)

    def bind(self, prefix, namespace, *args, **kwargs):
        """ Extends the function to add an attribute to the class for each 
        added namespace to allow for use of dot notation. All prefixes are 
        converted to lowercase

        Args:
            prefix: string of namespace name
            namespace: rdflib.namespace instance

        Example usage:
            RdfNsManager.rdf.type => 
                    http://www.w3.org/1999/02/22-rdf-syntax-ns#type

        """
        # convert all prefix names to lowercase
        prefix = str(prefix).lower()
        #! treat 'graph' as a reserved word and convert it to graph1 
        if prefix == "graph":
            prefix == "graph1"
        if not isinstance(namespace, Namespace):
            namespace = Namespace(self.clean_iri(namespace))
        super(RdfNsManager, self).bind(prefix, namespace, *args, **kwargs)
        # remove all namespace attributes from the class
        ns_attrs = inspect.getmembers(RdfNsManager,
                                      lambda a:not(inspect.isroutine(a)))
        for attr in ns_attrs:
            if isinstance(attr[1], Namespace):
                delattr(RdfNsManager, attr[0])

        # cycle through the namespaces and add them to the class
        for prefix, namespace in self.store.namespaces():
            setattr(RdfNsManager, prefix, Namespace(namespace))

    def prefix(self, format_type="sparql"):
        ''' Generates a string of the rdf namespaces listed used in the
            framework
            
            formatType: "sparql" or "turtle"
        '''
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        _return_str = ""
        for _prefix, _ns in self.store.namespaces():
            if format_type.lower() == "sparql":
                _return_str += "PREFIX {0}: <{1}>\n".format(_prefix, _ns)
            elif format_type.lower() == "turtle":
                _return_str += "@prefix {0}: <{1}> .\n".format(_prefix, _ns)
        return _return_str

    def load(self, filepath, file_encoding=None):
        """ Reads the the beginning of a turtle file and sets the prefix's used
        in that file and sets the prefix attribute 

        Args:
            filepath: the path to the turtle file
            file_encoding: specify a specific encoding if necessary
        """
        with open(filepath, encoding=file_encoding) as inf:
            for line in inf:
                current_line = str(line).strip()
                if current_line.startswith("@prefix"):
                    self._add_ttl_ns(current_line.replace("\n",""))
                elif len(current_line) > 10:
                    break
    def dict_load(self, ns_dict):
        """ Reads a dictionary of namespaces and binds them to the manager

        Args:
            ns_dict: dictionary with the key as the prefix and the value
                     as the uri
        """
        for prefix, uri in ns_dict.items():
            self.bind(prefix, uri)

    def _add_ttl_ns(self, line):
        """ takes one prefix line from the turtle file and binds the namespace
        to the class

        Args:
            line: the turtle prefix line string
        """
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)

        lg.debug("line:\n%s", line)
        line = str(line).strip()
        # if the line is not a prefix line exit
        if line is None or line == 'none' or line == '' \
                or not line.lower().startswith('@prefix'):
            return
        # parse the turtle line
        line = line.replace("@prefix","",1).strip()
        if line.endswith("."):
            line = line[:-1]
        prefix = line[:line.find(":")].strip()
        uri = clean_iri(line[line.find(":")+1:].strip())
        # add the namespace to the class
        lg.debug("\nprefix: %s  uri: %s", prefix, uri)
        self.bind(prefix, Namespace(uri))

    def iri(self, uri_string):
        return iri(uri_string)

    def clean_iri(self, uri_string):
        return clean_iri(uri_string)

    def pyuri(self, value):
        return pyuri(value)

    def ttluri(self, value):
        return ttluri(value)

    def nouri(self, value):
        return nouri(value)

    def uri_prefix(self, value):
        return uri_prefix(value)