''' contains functions for converting objects to namespace prefixes '''
import re
import inspect
import logging
import pdb

from rdflib import Namespace, Graph, URIRef
from rdflib.namespace import NamespaceManager
from rdfframework.utilities.uriconvertor import iri, uri, pyuri, ttluri, nouri, uri_prefix, \
        clean_iri
__author__ = "Mike Stabile, Jeremy Nelson"

NS_OBJ = None
NS_GRAPH = Graph()
DEBUG = True
# set the modulename
MNAME = inspect.stack()[0][1]


def get_ns_obj(ns_obj=None, config=None):
    """ returns an instance of the RdfNsManager

    Args:
        *ns_obj: an RdfNsManager instance or None
        *config: the config dict/obj for the application

    * Optional
    """
    global NS_OBJ
    if ns_obj is None and NS_OBJ is None:
        try:
            from rdfframework import get_framework
            ns_obj = get_framework().ns_obj
            if ns_obj is None:
                ns_obj = RdfNsManager(config=config)
                NS_OBJ = ns_obj
        except:
            if isinstance(NS_OBJ, RdfNsManager):
                ns_obj = NS_OBJ
            else:
                ns_obj = RdfNsManager(config=config)
                NS_OBJ = ns_obj
    else:
        ns_obj = NS_OBJ
    return ns_obj


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
        # cylce through the namespace section and add to the return obj
        for _ns in _ns_obj:
            _prefix_key = "http://knowledgelinks.io/ns/data-structures/prefix"
            _ns_key = 'http://knowledgelinks.io/ns/data-structures/nameSpaceUri'
            NS_OBJ.bind(_ns.get(_prefix_key), Namespace(_ns.get(_ns_key)))
    elif filepaths:
        for path in filepaths:
            NS_OBJ.load(path)
    return NS_OBJ

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
        # remove the item form the namespace dict 
        namespace = str(namespace)
        for ns in list(self.store._IOMemory__namespace.items()):
            if str(ns[0]) == namespace or str(ns[1]) == namespace:
                del self.store._IOMemory__namespace[ns[0]]
        # remove the item form the namespace dict 
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
        return uri(value, strip_iri=strip_iri, ns_obj=self)
