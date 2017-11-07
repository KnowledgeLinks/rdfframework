''' Manager for managing application wide RDF namespaces '''
import re
import inspect
import logging
import binascii
import base64
from rdflib import Namespace, Graph, URIRef
from rdflib.namespace import NamespaceManager


__author__ = "Mike Stabile, Jeremy Nelson"

NS_OBJ = None
NS_GRAPH = Graph()
DEBUG = True
# set the modulename
MNAME = inspect.stack()[0][1]

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

    fw_namespaces = {
        "kds": "http://knowledgelinks.io/ns/data-structures/",
        "kdr": "http://knowledgelinks.io/ns/data-resources/",
        "owl": "http://www.w3.org/2002/07/owl#"
    }

    def __init__(self, *args, **kwargs):
        global NS_GRAPH
        graph = NS_GRAPH
        config = None
        if 'config' in kwargs:
            config = kwargs.pop("config")
        self.ns_dict = {}
        self.uri_dict = {}
        super(RdfNsManager, self).__init__(graph, *args, **kwargs)
        self.dict_load(self.fw_namespaces)

        # load default ns's from config info
        if config and hasattr(config, "DEFAULT_RDF_NS"):
            self.dict_load(config.DEFAULT_RDF_NS)
    @property
    def make_dicts(self):
        ns_dict = {key: str(value) for key, value in self.namespaces()}
        # pdb.set_trace()
        for key, value in ns_dict.items():
            self.ns_dict[value] = value
            self.ns_dict[key] = value
        uri_dict = {str(value): key for key, value in self.namespaces()}
        for key, value in uri_dict.items():
            self.uri_dict[value] = value
            self.uri_dict[key] = value


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
        calc = kwargs.pop('calc', True)
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
        if calc:
            self.make_dicts

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
        self.make_dicts

    def dict_load(self, ns_dict):
        """ Reads a dictionary of namespaces and binds them to the manager

        Args:
            ns_dict: dictionary with the key as the prefix and the value
                     as the uri
        """
        for prefix, uri in ns_dict.items():
            self.bind(prefix, uri, override=False, calc=False)
        self.make_dicts

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
        self.bind(prefix, Namespace(uri), override=False, calc=False)

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

    def pyuri(self, value):
        """ converts a ttl or full uri to an ns_value format """
        return self.convert_to_ns(value)

    def ttluri(self, value):
        ''' converts an iri to the app defined rdf namespaces in the framework
        in a turtle accessable format. i.e. schema_name or
        http:schema.org/name  --> schema:name '''
        return self.convert_to_ttl(value)

    def nouri(self, value):
        """ removes all of the namespace portion of the uri
        i.e. http://www.schema.org/name  becomes name

        Args:
            value: the uri to convert
        Returns:
            stripped value from namespace
        """
        return self.parse_uri(value)[1]

    def uri(self, value):
        """ Converts py_uri or ttl uri to a http://... full uri format

        Args:
            value: the string to convert

        Returns:
            full uri of an abbreivated uri
        """

        return self.convert_to_uri(value)

    def convert_to_uri(self, value):
        ''' converts a prefixed rdf ns equivalent value to its uri form.
            If not found returns the value as is

            args:
                value: the URI/IRI to convert
                strip_iri: removes the < and > signs
                rdflib_uri: returns an rdflib URIRef
            '''
        parsed = self.parse_uri(str(value))

        try:
            return "%s%s" % (self.ns_dict[parsed[0]], parsed[1])
        except KeyError:
            return self.rpyhttp(value)

    def uri_prefix(self, value):
        ''' Takes a uri and returns the prefix for that uri '''

        return self.ns_dict[self.parse_uri(value)[0]]

    @staticmethod
    def rpyhttp(value):
        """ converts a no namespace pyuri back to a standard uri """
        if value.startswith("http"):
            return value
        try:
            parts = value.split("_")
            del parts[0]
            _uri = base64.b64decode(parts.pop(0)).decode()
            return _uri + "_".join(parts)
        except (IndexError, UnicodeDecodeError, binascii.Error):
            # if the value is not a pyuri return the value
            return value

    def pyhttp(self, value):
        """ converts a no namespaces uri to a python excessable name """
        if value.startswith("pyuri_"):
            return value
        value = self.clean_iri(str(value))
        ending = re.sub(r"^(.*[#/])", "", value)
        trim_val = len(ending)
        if trim_val == 0:
            start = value
        else:
            start = value[:-trim_val]
        return "pyuri_%s_%s" % (base64.b64encode(bytes(start,"utf-8")).decode(),
                                ending)
    @staticmethod
    def clean_iri(uri_string):
        '''removes the <> signs from a string start and end'''
        uri_string = str(uri_string)
        if isinstance(uri_string, str):
            uri_string = uri_string.strip()
            if uri_string[:1] == "<" and uri_string[len(uri_string)-1:] == ">":
                uri_string = uri_string[1:len(uri_string)-1]
        return uri_string

    @staticmethod
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

    def convert_to_ttl(self, value):
        ''' converts a value to the prefixed rdf ns equivalent. If not found
            returns the value as is.

        args:
            value: the value to convert
        '''

        parsed = self.parse_uri(value)

        try:
            rtn_val = "%s:%s" % (self.uri_dict[parsed[0]], parsed[1])
        except KeyError:
            rtn_val = self.iri(self.rpyhttp(value))

        return rtn_val

    def convert_to_ns(self, value):
        ''' converts a value to the prefixed rdf ns equivalent. If not found
            returns the value as is

        args:
            value: the value to convert
        '''
        parsed = self.parse_uri(value)

        try:
            rtn_val = "%s_%s" % (self.uri_dict[parsed[0]], parsed[1])
        except KeyError:
            rtn_val = self.pyhttp(value)
        return rtn_val

    @staticmethod
    def parse_uri(value):
        """ Parses a value into a head and tail pair based on the finding the
            last '#' or '/' as is standard with URI fromats

        args:
            value: string value to parse

        returns:
            tuple: (lookup, end)
        """
        value = value.replace("<","").replace(">","")
        lookup = None
        end = None

        try:
            lookup = value[:value.rindex('#')+1]
            end = value[value.rindex('#')+1:]
        except ValueError:
            try:
                lookup = value[:value.rindex('/')+1]
                end = value[value.rindex('/')+1:]
            except ValueError:
                try:
                    lookup = value[:value.index(':')]
                    end = value[value.rindex(':')+1:]
                except ValueError:
                    try:
                        lookup = value[:value.index('_')]
                        end = value[value.index('_')+1:]
                    except ValueError:
                        lookup = value
                        end = ""

        return (lookup, end)
