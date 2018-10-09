import json
import pdb
import re
import inspect
import logging
import binascii
import base64
import functools
import rdflib

from rdfframework.utilities import cbool, is_not_null, DictClass, new_id, \
        memorize, RegInstanceMeta, RegPerformInstanceMeta, clean_iri
from .datatypeerrors import NsPrefixExistsError, NsUriExistsError, \
        NsUriBadEndingError
from .uriformatters import http_formatter, uri_formatter, ttl_formatter, \
        pyuri_formatter, rdflib_formatter, xmletree_formatter

import base64

__author__ = "Mike Stabile, Jeremy Nelson"

DEBUG = True
# set the modulename
MNAME = inspect.stack()[0][1]

# list of attributes for datatypes that are property objects that can be
# removed by the PerfromaceMeta class so that string values can be set during
# class instanciation
PERFORMANCE_ATTRS = ['sparql', 'sparql_uri', 'pyuri', 'clean_uri']

def format_json(item, **kwargs):
    """ formats a datatype object to a json value """
    try:
        json.dumps(item.value)
        return item.value
    except TypeError:
        if 'time' in item.class_type.lower() \
                or 'date' in item.class_type.lower():
            return item.value.isoformat()
        raise

def format_sparql(item, dt_format='turtle', **kwargs):
    """
    Formats a datatype value to a SPARQL representation

    args:
        item: the datatype object
        dt_format: the return format ['turtle', 'uri']
    """
    try:
        rtn_val = json.dumps(item.value)
        rtn_val = item.value
    except:
        if 'time' in item.class_type.lower() \
                or 'date' in item.class_type.lower():
            rtn_val = item.value.isoformat()
        else:
            rtn_val = str(item.value)
    if hasattr(item, "datatype"):
        if hasattr(item, "lang") and item.lang:
            rtn_val = '%s@%s' % (json.dumps(rtn_val), item.lang)
        else:
            dt = item.datatype
            if dt_format == "uri":
                dt = item.datatype.sparql_uri
            if item.datatype in ["xsd_string",
                                 "xsd_dateTime",
                                 "xsd_time",
                                 "xsd_date"]:
                rtn_val = json.dumps(rtn_val)
            else:
                rtn_val = '"%s"' % json.dumps(rtn_val)
            rtn_val = '%s^^%s' % (rtn_val, dt.sparql)
    return rtn_val

def format_pyuri(item, **kwargs):
    """
    Formats the datatype into a python friendly repesentation

    args:
        item: the datatype object to convert
    """
    try:
        return NSM.pyuri(item.value)
    except AttributeError:
        pass

__FORMAT_OPTIONS__ = {
    "sparql": format_sparql,
    "json": format_json,
    "pyuri": format_pyuri
}

class BaseRdfDataType(metaclass=RegInstanceMeta):
    """ Base for all rdf datatypes. Not designed to be used alone """
    __required_idx_attrs__ = {"class_type"}
    __optional_idx_attrs__ = {"datatype", "py_type"}
    __special_idx_attrs__ = [{"datatype": ["sparql",
                                           "sparql_uri",
                                           "pyuri",
                                           "clean_uri",
                                           "rdflib",
                                           "etree"]}]
    __nested_idx_attrs__ = {"type"}
    type = "literal"
    default_method = "sparql"
    class_type = "RdfDataType"

    def __init__(self, value):
        self.value = value

    def _format(self, method="sparql", dt_format="turtle"):
        """
        Rormats the value in various formats

        args:
            method: ['sparql', 'json', 'pyuri']
            dt_format: ['turtle','uri'] used in conjuction with the 'sparql'
                       method

        """

        try:
            return __FORMAT_OPTIONS__[method](self, dt_format=dt_format)
        except KeyError:
            raise NotImplementedError("'{}' is not a valid format method"
                                      "".format(method))

    def __repr__(self):
        return self._format(method=self.default_method)

    def __str__(self):
        return str(self.value)
        #return self._format(method="sparql")

    @property
    def sparql(self):
        return self._format(method="sparql")

    @property
    def sparql_uri(self):
        return self._format(method="sparql", dt_format="uri")

    @property
    def pyuri(self):
        return self._format(method="pyuri")

    @property
    def debug(self):
        return DictClass(self)

    @property
    def to_json(self):
        return self._format(method="json")

    @property
    def rdflib(self):
        return rdflib.Literal(self.value, datatype=self.datatype.rdflib)

    def __call__(self):
        return


# @functools.lru_cache(maxsize=10000)
class Uri(BaseRdfDataType, str, metaclass=RegPerformInstanceMeta):
    """ URI/IRI class for working with RDF data """
    class_type = "Uri"
    type = "uri"
    default_method = "pyuri"
    es_type = "text"
    performance_mode = True
    performance_attrs = PERFORMANCE_ATTRS

    def __new__(cls, *args, **kwargs):
        value = args[0]
        if not isinstance(args[0], tuple):
            value = NSM.get_uri_parts(args[0])
        args = [pyuri_formatter(*value)]
        newobj = str.__new__(cls, *args)
        newobj.value = value
        newobj.pyuri = args[0]
        return newobj

    def __init__(self, value):
        # if the performance_mode is set than the value for the listed
        # attributes is calculated at instanciation
        if self.performance_mode:
            for attr in self.performance_attrs:
                if attr != 'pyuri':
                    setattr(self, attr, str(getattr(self, "__%s__" % attr)))
        self.hash_val = hash(self.pyuri)

    # def __call__(self):
    #     return
    # __wrapped__ = Uri
    # def __eq__(self, value):
    #     if not isinstance(value, Uri.__wrapped__):
    #         # pdb.set_trace()
    #         value = Uri(value)
    #     if self.value == value.value:
    #         return True
    #     return False

    @property
    def sparql(self):
        """ Returns the URI in a SPARQL format """
        return ttl_formatter(*self.value)

    @property
    def sparql_uri(self):
        """ Returns the URI in a full http format with '<' and '>'
            encapsulation
        """
        return uri_formatter(*self.value)

    @property
    def to_json(self):
        """ Returns the json formatting """
        return self.clean_uri

    @property
    def rdflib(self):
        """ Returns the rdflibURI reference """
        return rdflib_formatter(*self.value)

    @property
    def clean_uri(self):
        """ Returns the URI in a full http format WITHOUT '<' and '>'
            encapsulation
        """
        return http_formatter(*self.value)

    @property
    def etree(self):
        """
        Returns string in the python xml etree format
        """
        return xmletree_formatter(*self.value)

    def __str__(self):
        return self.clean_uri
        # return self.sparql

    def __repr__(self):
        return self.pyuri

    def __hash__(self):
        return self.hash_val

def rdfuri_formatter(namespace, value):
    """ Formats a namespace and ending value into an instance of the
    rdfframework Uri class

    args:
        namespace: RdfNamespace or tuple in the format of (prefix, uri,)
        value: end value to attach to the namespace
    """
    return Uri((namespace, value))

class RdfNamespaceMeta(type):
    """ Metaclass ensures that there is only one prefix and uri instanciated
    for a particular namespace """

    _ns_instances = []

    def __is_new_ns__(cls, namespace):
        """ cycles through the instanciated namespaces to see if it has already
        been created

        args:
            namespace: tuple of prefix and uri to check
        """

        for ns in cls._ns_instances:
            if ns[0] == namespace[0] and ns[1] == namespace[1]:
                return ns
            elif ns[0] == namespace[0] and ns[1] != namespace[1]:
                raise NsPrefixExistsError(namespace,
                                          ns,
                                          "prefix [%s] already assigned to [%s]" %
                                          (namespace, ns[1]))
            elif ns[0] != namespace[0] and ns[1] == namespace[1]:
                raise NsUriExistsError(namespace,
                                       ns,
                                       "uri [%s] already assigned to [%s]" %
                                       (namespace, ns[0]))
        return True

    @staticmethod
    def __format_args__(*args):
        """ formats the args so that prefix is lowercased and validates the
            uri
        """
        ns_uri = RdfNsManager.clean_iri(str(args[1])).strip()
        if ns_uri[-1] not in ['/', '#']:
            raise NsUriBadEndingError("incorrect ending for '%s', '%s'" %
                                      args[:2])
        return (args[0].lower(), ns_uri)

    def __call__(cls, *args, **kwargs):

        try:
            args = cls.__format_args__(*args)
            is_new = cls.__is_new_ns__(args)
            if is_new == True:
                new_ns = super(RdfNamespaceMeta, cls).__call__(*args, **kwargs)
                cls._ns_instances.append(new_ns)
                try:
                    NSM.bind(new_ns[0], new_ns[1])
                except NameError:
                    pass
                return new_ns
            return is_new
        except (NsUriExistsError,
                NsPrefixExistsError,
                NsUriBadEndingError) as err:
            if kwargs.get('override') == True:
                setattr(err.old_ns, '__ns__' , err.new_ns)
                return err.old_ns
            elif kwargs.get('ignore_errors', False):
                return err.old_ns
            raise err

    def __iter__(cls):
        return iter(cls._ns_instances)

class RdfNamespace(metaclass=RdfNamespaceMeta):
    """ A namespace is composed of a prefix and a URI

    args:
        prefix: short abbreviation for the uri
        uri: the full 'http...' format

    kwargs:
        formatter: processor that takes a args and returns a formated string
                args -> RdfNamespace and a value
                * This is so that you can set a application wide default return
                format for namespace (ttl or uri with or without <>)
        override(False): False raises error
                         True: replaces old ns paring with a new one.
                            old ('test', 'http://test.org/')
                            new ('test', 'http://TEST.org/')
                            sets old ns to ('test', 'http://TEST.org/')
        ignore_errors(False): No errors are raised during ns assignment and
                original ns is preserved
    """

    _formatter = rdfuri_formatter

    def __init__(self, prefix, uri, **kwargs):
        self.__dict__['__ns__'] = (prefix, uri)
        self.__dict__['_formatter'] = kwargs.get('formatter',
                                                 RdfNamespace._formatter)

    def __getattr__(self, attr):
        return self._formatter(self, attr)

    def __repr__(self):
        return "RdfNamespace(\"%s\", \"%s\")" % self.__ns__

    def __iter__(self):
        return iter(self.__ns__)

    def __str__(self):
        return self._sparql_

    @property
    def _ttl_(self):
        return "@prefix %s: <%s> ." % (self.__ns__)

    @property
    def _sparql_(self):
        return "prefix %s: <%s>" % (self.__ns__)

    @property
    def _xml_(self):
        return "xmlns:%s=%s" % (self.__ns__[0], json.dumps(self.__ns__[1]))

    def __getitem__(self, idx):
        return self.__ns__[idx]

    def __setattr__(self, attr, value):
        if attr == '__ns__':
            print("changing_ns")
            if self.__dict__.get(attr) and self.__dict__[attr][0] != value[0]:
                print("removing NSM attr")
                delattr(NSM, self.__dict__[attr][0])
            self.__dict__[attr] = value
            setattr(NSM, value[0], self)

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
            if 'config' in kwargs and hasattr(kwargs['config'],
                                              "NAMESPACES"):
                cls._instances[cls].dict_load(kwargs['config'].NAMESPACES)
            try:
                ns_arg = args[0]
                if isinstance(ns_arg, dict):
                    cls._instances[cls].dict_load(ns_arg)
            except IndexError:
                pass
        return cls._instances[cls]

class RdfNsManager(metaclass=NsmSingleton):
    """ Extends the the rdflib Namespace Manager. Provides additional methods
    to easily generate prefixes in use thoughout the application

    *** Of Note: this is a singleton class and only one instance of it will
    every exisit. """

    ln = "%s-RdfNsManager" % MNAME
    log_level = logging.CRITICAL

    # The below are default namespaces that are always loaded
    fw_namespaces = {
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "kds": "http://knowledgelinks.io/ns/data-structures/",
        "kdr": "http://knowledgelinks.io/ns/data-resources/",
        "owl": "http://www.w3.org/2002/07/owl#",
        "dcterm": "http://purl.org/dc/terms/"
    }

    def __init__(self, *args, **kwargs):
        config = None
        if 'config' in kwargs:
            config = kwargs.pop("config")
        self.ns_dict = {}
        self.uri_dict = {}
        self.dict_load(self.fw_namespaces)
        # load default ns's from config info
        if config and hasattr(config, "DEFAULT_RDF_NS"):
            self.dict_load(config.DEFAULT_RDF_NS)


    @property
    def __make_dicts__(self):
        """ creates a reference dictionary for rapid lookup of a namespace """
        self.ns_dict = {}
        for ns in self.namespaces:
            self.ns_dict[ns[0]] = ns
            self.ns_dict[ns[1]] = ns

    def bind(self, prefix, namespace, *args, **kwargs):
        """ Extends the function to add an attribute to the class for each
        added namespace to allow for use of dot notation. All prefixes are
        converted to lowercase

        Args:
            prefix: string of namespace name
            namespace: rdflib.namespace instance

        kwargs:
            calc: whether or not create the lookup reference dictionaries

        Example usage:
            RdfNsManager.rdf.type =>
                    http://www.w3.org/1999/02/22-rdf-syntax-ns#type

        """
        # RdfNamespace(prefix, namespace, **kwargs)
        setattr(self, prefix, RdfNamespace(prefix, namespace, **kwargs))
        if kwargs.pop('calc', True):
            self.__make_dicts__

    def prefix(self, format="sparql"):
        ''' Generates a string of the rdf namespaces listed used in the
            framework

            format: "sparql" or "turtle"
        '''

        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)

        _return_str = ""
        if format.lower() == "sparql":
            return "\n".join([ns._sparql_ for ns in self.namespaces])
        elif format.lower() in ["turtle", "ttl"]:
            return "\n".join([ns._ttl_ for ns in self.namespaces])
        elif format.lower() in ["rdf", "xml", "rdf/xml"]:
            return "<rdf:RDF %s>" % \
                    " ".join([ns._xml_ for ns in self.namespaces])
        else:
            raise NotImplementedError("'%s' is not a valid prefix type." %
                                      format)

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
        self.__make_dicts__

    @property
    def namespaces(self):
        return iter(RdfNamespace)

    def dict_load(self, ns_dict):
        """ Reads a dictionary of namespaces and binds them to the manager

        Args:
            ns_dict: dictionary with the key as the prefix and the value
                     as the uri
        """
        for prefix, uri in ns_dict.items():
            self.bind(prefix, uri, override=False, calc=False)
        self.__make_dicts__

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
        uri = self.clean_iri(line[line.find(":")+1:].strip())
        # add the namespace to the class
        lg.debug("\nprefix: %s  uri: %s", prefix, uri)
        self.bind(prefix, uri, override=False, calc=False)

    def del_ns(self, namespace):
        """ will remove a namespace ref from the manager. either Arg is
        optional.

        args:
            namespace: prefix, string or Namespace() to remove
        """
        # remove the item from the namespace dict
        namespace = str(namespace)
        attr_name = None
        if hasattr(self, namespace):
            delattr(self, namespace)


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

    def uri(self, value, strip_iri=True):
        """ Converts py_uri or ttl uri to a http://... full uri format

        Args:
            value: the string to convert

        Returns:
            full uri of an abbreivated uri
        """

        return self.convert_to_uri(value, strip_iri=strip_iri)

    def convert_to_uri(self, value, strip_iri=True):
        ''' converts a prefixed rdf ns equivalent value to its uri form.
            If not found returns the value as is

            args:
                value: the URI/IRI to convert
                strip_iri: removes the < and > signs
                rdflib_uri: returns an rdflib URIRef
            '''
        parsed = self.parse_uri(str(value))

        try:
            new_uri = "%s%s" % (self.ns_dict[parsed[0]], parsed[1])
            if not strip_iri:
                return self.iri(new_uri)
            return new_uri
        except KeyError:
            return self.rpyhttp(value)

    def get_uri_parts(self, value):
        """takes an value and returns a tuple of the parts

        args:
            value: a uri in any form pyuri, ttl or full IRI
        """
        if value.startswith('pyuri_'):
            value = self.rpyhttp(value)
        parts = self.parse_uri(value)
        try:
            return (self.ns_dict[parts[0]], parts[1])
        except KeyError:
            try:
                return (self.ns_dict[parts[0].lower()], parts[1])
            except KeyError:
                return ((None, parts[0]), parts[1])


    def uri_prefix(self, value):
        ''' Takes a uri and returns the prefix for that uri '''

        return self.ns_dict[self.parse_uri(value)[0]][0]

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
        parts = self.parse_uri(value)
        return "pyuri_%s_%s" % (base64.b64encode(bytes(parts[0],
                                                       "utf-8")).decode(),
                                parts[1])
    @staticmethod
    def clean_iri(uri_string):
        '''removes the <> signs from a string start and end

        ags:
            uri_string: the uri string
        '''
        return clean_iri(uri_string)

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
        value = RdfNsManager.clean_iri(value)
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

NSM = RdfNsManager()
