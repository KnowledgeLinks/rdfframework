''' contains functions for converting objects to namespace prefixes '''
import re
import inspect
import logging
import pdb
import base64
from rdflib import Namespace, Graph, URIRef
from rdflib.namespace import NamespaceManager

__author__ = "Mike Stabile, Jeremy Nelson"

NS_OBJ = None
NS_GRAPH = Graph()
DEBUG = True
# set the modulename
MNAME = inspect.stack()[0][1]

def convert_to_ns(value):
    ''' converts a value to the prefixed rdf ns equivalent. If not found
        returns the value as is 
    
    args:
        value: the value to convert
    '''
    ns_obj = RdfNsManager()
    for _prefix, _ns_uri in ns_obj.namespaces():
        if str(value).startswith(_prefix + ":") or \
                str(value).startswith("<%s:" % _prefix):
            return value.replace(_prefix + ":", _prefix + "_").replace(\
                    "<","").replace(">","")
        if str(value).startswith(str(_ns_uri)) or str(value).startswith("<"+str(_ns_uri)):
            return value.replace(str(_ns_uri), _prefix + "_").replace(\
                    "<","").replace(">","")
    return value

def convert_to_ttl(value):
    ''' converts a value to the prefixed rdf ns equivalent. If not found
        returns the value as is.

    args:
        value: the value to convert
    '''
    ns_obj = RdfNsManager()
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

def convert_to_uri(value, strip_iri=False, rdflib_uri=False):
    ''' converts a prefixed rdf ns equivalent value to its uri form.
        If not found returns the value as is 

        args:
            value: the URI/IRI to convert
            strip_iri: removes the < and > signs
            rdflib_uri: returns an rdflib URIRef
    '''

    ns_obj = RdfNsManager()

    value = str(value).replace("<","").replace(">","")
    if value.startswith("pyuri_"):
        parts = value.split("_")
        value = base64.b64decode(parts[1]).decode() + parts[2]
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
        ns_obj = RdfNsManager()

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
                    _return_list.append(convert_to_ns(item))
        return _return_list
    elif isinstance(obj, dict):
        _return_obj = {}
        for key, item in obj.items():
            nkey = convert_to_ns(key)
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
                    _return_obj[nkey] = convert_to_ns(item)
        return _return_obj
    else:
        if key_only: 
            if rdflib_uri:
                #pdb.set_trace()
                return convert_to_uri(item, rdflib_uri=True)
            else:
                return obj
        else:
            return convert_to_ns(obj)

def pyuri(value):
    ''' converts an iri to the app defined rdf namespaces in the framework
        in a python accessable format. i.e. schema:name or
        http:schema.org/name  --> schema_name '''
    if str(value).startswith("http"):
        rtn_val =  convert_to_ns(value)
    else:
        rtn_val = convert_to_ns(convert_to_uri(value))
    if rtn_val.startswith("http"):
        rtn_val = pyhttp(rtn_val)
    return rtn_val

def pyhttp(value):
    """ converts a no namespaces uri to a python excessable name """

    ending = re.sub(r"^(.*[#/])", "", clean_iri(str(value)))
    trim_val = len(ending)
    if trim_val == 0:
        start = value
    else:
        start = value[:-trim_val]
    return "pyuri_%s_%s" % (base64.b64encode(bytes(start,"utf-8")).decode(),
                            ending)


def ttluri(value):
    ''' converts an iri to the app defined rdf namespaces in the framework
        in a turtle accessable format. i.e. schema_name or
        http:schema.org/name  --> schema:name '''

    if str(value).startswith("http"):
        return convert_to_ttl(value)
    else:
        return convert_to_ttl(convert_to_uri(value))

def nouri(value):
    """ removes all of the namespace portion of the uri 
    i.e. http://www.schema.org/name  becomes name

    Args:
        value: the uri to convert
    Returns:
        stripped value from namespace
    """
    _uri = None
    if not clean_iri(str(value)).startswith("http"):
        _uri = convert_to_uri(value)
    else:
        _uri = value
    if _uri:
        return re.sub(r"^(.*[#/])", "", clean_iri(str(_uri)))
    else:
        return value

def uri_prefix(value):
    ''' Takes a uri and returns the prefix for that uri '''
    if not DEBUG:
        debug = False
    else:
        debug = False
    if debug: print("START uri_prefix() uriconvertor.py -------------------\n")
    _uri = None
    if not clean_iri(str(value)).startswith("http"):
        _uri = convert_to_uri(str(value))
    else:
        _uri = str(value)
    _ns_uri = clean_iri(
            _uri.replace(re.sub(r"^(.*[#/])", "", clean_iri(str(_uri))),""))
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

def uri(value, strip_iri=False):
    """ Converts py_uri or ttl uri to a http://... full uri format 

    Args:
        value: the string to convert

    Returns:
        full uri of an abbreivated uri
    """

    if clean_iri(str(value)).startswith("http"):
        if strip_iri:
            return clean_iri(str(value))
        else:
            return iri(value)
    else:
        return convert_to_uri(value, strip_iri=strip_iri)

# def get_ns_obj(ns_obj=None, config=None):
#     """ returns an instance of the RdfNsManager

#     Args:
#         *ns_obj: an RdfNsManager instance or None
#         *config: the config dict/obj for the application

#     * Optional
#     """
#     global NS_OBJ
#     if ns_obj is None and NS_OBJ is None:
#         try:
#             from rdfframework.getframework import get_framework
#             ns_obj = get_framework().ns_obj
#             if ns_obj is None:
#                 ns_obj = RdfNsManager(config=config)
#                 NS_OBJ = ns_obj
#         except:
#             if isinstance(NS_OBJ, RdfNsManager):
#                 ns_obj = NS_OBJ
#             else:
#                 ns_obj = RdfNsManager(config=config)
#                 NS_OBJ = ns_obj
#     else:
#         ns_obj = NS_OBJ
#     if config and hasattr(config, "DEFAULT_RDF_NS"):
#         ns_obj.dict_load(config.DEFAULT_RDF_NS)
#         NS_OBJ = NS_OBJ
#     return ns_obj

def iris_to_strings(obj, ns_obj=None):
    #ns_obj = get_ns_obj(ns_obj)
    ns_obj = RdfNsManager()

    if isinstance(obj, list):
        _return_list = []
        for item in obj:
            if isinstance(item, list):
                _return_list.append(iris_to_strings(item, ns_obj))
            elif isinstance(item, dict):
                _return_list.append(iris_to_strings(item, ns_obj))
            else:
                 _return_list.append(convert_to_uri(item, True))
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
                _return_obj[nkey] = convert_to_uri(item, True)
        return _return_obj
    else:
        return convert_to_uri(obj, True)

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

class NsmSingleton(type):
    """Singleton class for the RdfNsManager that will allow for only one
    instance of the RdfNsManager to be created. In addition the app config
    can be sent to the RdfNsManger even after instantiation so the the 
    default RDF namespaces can be loaded. """

    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(NsmSingleton, 
                    cls).__call__(*args, **kwargs)
        else:
            if 'config' in kwargs and hasattr(kwargs['config'], 
                                              "DEFAULT_RDF_NS"):
                cls._instances[cls].dict_load(kwargs['config'].DEFAULT_RDF_NS)
        return cls._instances[cls]

class RdfNsManager(NamespaceManager, metaclass=NsmSingleton):
    """ Extends the the rdflib Namespace Manager. Provides additional methods
    to easily generate prefixes in use thoughout the application 

    *** Of Note: this is a singleton class and only one instance of it will
    every exisit. """

    ln = "%s-RdfNsManager" % MNAME
    log_level = logging.CRITICAL

    def __init__(self, *args, **kwargs):
        global NS_GRAPH
        graph = NS_GRAPH
        config = None
        if 'config' in kwargs:
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
        if namespace in [ns for pre, ns in self.namespaces()]:
            self.del_ns(namespace)
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

        self.uri_list = list([str(uri) for pre, uri in self.namespaces()])

    def prefix(self, format="sparql"):
        ''' Generates a string of the rdf namespaces listed used in the
            framework
            
            format: "sparql" or "turtle"
        '''
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        _return_str = ""
        for _prefix, _ns in self.store.namespaces():
            if format.lower() == "sparql":
                _return_str += "PREFIX {0}: <{1}>\n".format(_prefix, _ns)
            elif format.lower() == "turtle":
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
            self.bind(prefix, uri, override=False)

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
        self.bind(prefix, Namespace(uri), override=False)

    def del_ns(self, namespace):
        """ will remove a namespace ref from the manager. either Arg is 
        optional.

        args:
            namespace: prefix, string or Namespace() to remove
        """
        # remove the item from the namespace dict 
        namespace = str(namespace)
        attr_name = None
        for ns in list(self.store._IOMemory__namespace.items()):
            if str(ns[0]) == namespace or str(ns[1]) == namespace:
                del self.store._IOMemory__namespace[ns[0]]
                # remove the attribute from the class
                delattr(RdfNsManager, ns[0])
        # remove the item from the namespace dict 
        for ns in list(self.store._IOMemory__prefix.items()):
            if str(ns[0]) == namespace or str(ns[1]) == namespace:
                del self.store._IOMemory__prefix[ns[0]]

    def iri(self, uri_string):
        """ adds <> signs to a uri value """
        return iri(uri_string)

    def clean_iri(self, uri_string):
        """ removes the <> signs from an uri value """
        return clean_iri(uri_string)

    def pyuri(self, value):
        """ converts a ttl or full uri to an ns_value format """
        return pyuri(value)

    def ttluri(self, value):
        """ converts ns_value of full uri to ttl format """
        return ttluri(value)

    def nouri(self, value):
        """ returns the value portion of a uri ns:value -> value """
        return nouri(value)

    def uri_prefix(self, value):
        """ returns the prefix protion from the ns:value -> ns """
        return uri_prefix(value)

    def uri(self, value, strip_iri=False):
        return uri(value, strip_iri=strip_iri)


def create_namespace_obj(obj=None, filepaths=None):
    ''' takes initial rdf application definitions and reads the namespaces '''
    global NS_OBJ
    if not NS_OBJ:
        NS_OBJ = RdfNsManager()
    _ns_obj = {}
    if obj:
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
        #return_obj = RdfNsManager()
        # cylce through the namespace section and add to the return obj
        for _ns in _ns_obj:
            _prefix_key = "http://knowledgelinks.io/ns/data-structures/prefix"
            _ns_key = 'http://knowledgelinks.io/ns/data-structures/nameSpaceUri'
            NS_OBJ.bind(_ns.get(_prefix_key), Namespace(_ns.get(_ns_key)))
    elif filepaths:
        for path in filepaths:
            NS_OBJ.load(path)
    return NS_OBJ
