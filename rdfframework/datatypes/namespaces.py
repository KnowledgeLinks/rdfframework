import json
import pdb
import re
import inspect
import logging
import binascii
import base64
import functools
import rdflib

# from decimal import Decimal
from rdfframework.utilities import cbool, is_not_null, DictClass, new_id, \
        memorize, PerformanceMeta, InstanceCheckMeta
# from dateutil.parser import parse
# from datetime import date, datetime, time, timezone
from .datatypeerrors import NsPrefixExistsError, NsUriExistsError, \
        NsUriBadEndingError
from .uriformatters import http_formatter, uri_formatter, ttl_formatter, \
        pyuri_formatter, rdflib_formatter

import base64

__author__ = "Mike Stabile, Jeremy Nelson"

DEBUG = True
# set the modulename
MNAME = inspect.stack()[0][1]

# list of attributes for datatypes that are property objects that can be
# removed by the PerfromaceMeta class so that string values can be set during
# class instanciation
PERFORMANCE_ATTRS = ['sparql', 'sparql_uri', 'pyuri', 'clean_uri']

class BaseRdfDataType(object, metaclass=InstanceCheckMeta):
    """ Base for all rdf datatypes. Not designed to be used alone """
    type = "literal"
    default_method = "sparql"
    py_type = None
    class_type = "RdfDataType"

    def __init__(self, value):
        self.value = value

    def _format(self, method="sparql", dt_format="turtle"):
        """ formats the value """

        try:
            rtn_val = json.dumps(self.value)
            rtn_val = self.value
        except:
            if 'time' in self.class_type.lower() \
                    or 'date' in self.class_type.lower():
                rtn_val = self.value.isoformat()
            else:
                rtn_val = str(self.value)
        if method in ['json', 'sparql']:
            if hasattr(self, "datatype"):
                if hasattr(self, "lang") and self.lang:
                    rtn_val = '%s@%s' % (json.dumps(rtn_val), self.lang)
                else:
                    dt = self.datatype
                    if dt_format == "uri":
                        dt = self.datatype.sparql_uri
                    if method == "sparql":
                        if self.datatype == "xsd:string":
                            rtn_val = json.dumps(rtn_val)
                        else:
                            rtn_val = '"%s"' % rtn_val
                        rtn_val = '%s^^%s' % (rtn_val, dt.sparql)
            elif method == "json":
                pass
            else:
                rtn_val = '"%s"^^xsd:string' % rtn_val
        elif method == "pyuri":
            rtn_val = NSM.pyuri(self.value)
        return rtn_val

    def __repr__(self):
        return self._format(method=self.default_method)

    def __str__(self):
        return str(self.value)

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
        return rdflib.Literal(self.value)


@functools.lru_cache(maxsize=1000)
class Uri(BaseRdfDataType, str, metaclass=PerformanceMeta):
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
        # if not isinstance(value, tuple):
        #     value = NSM.get_uri_parts(value)
        # self.value = value
        # if the performance_mode is set than the value for the listed
        # attributes is calculated at instanciation
        if self.performance_mode:
            for attr in self.performance_attrs:
                if attr != 'pyuri':
                    setattr(self, attr, str(getattr(self, "__%s__" % attr)))
        self.hash_val = hash(self.pyuri)

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

    # @property
    # def pyuri(self):
    #     """ Returns the URI in a python friendly format """
    #     return pyuri_formatter(*self.value)

    @property
    def to_json(self):
        """ Returns the json formatting """
        return self.sparql_uri

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

    # def __str__(self):
    #     return self.sparql

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
        "owl": "http://www.w3.org/2002/07/owl#"
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
        '''removes the <> signs from a string start and end'''
        uri_string = str(uri_string).strip()
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

# class BlankNode(BaseRdfDataType, metaclass=PerformanceMeta):
#     """ blankNode URI/IRI class for working with RDF data """
#     class_type = "BlankNode"
#     type = "bnode"
#     es_type = "text"
#     performance_mode = True
#     performance_attrs = PERFORMANCE_ATTRS

#     def __init__(self, value=None):
#         if value:
#             if not value.startswith("_:"):
#                 self.value = "_:" + value
#             else:
#                 self.value = value
#         else:
#             self.value = "_:" + new_id()
#         if self.performance_mode:
#             for attr in self.performance_attrs:
#                 setattr(self, attr, self.value)
#         self.hash_val = hash(self.value)

#     def __hash__(self):
#         return self.hash_val

# class XsdString(str, BaseRdfDataType):
#     """ String instance of rdf xsd:string type value"""

#     datatype = Uri("xsd:string")
#     class_type = "XsdString"
#     py_type = str
#     es_type = "text"

#     __slots__ = []

#     def __new__(cls, *args, **kwargs):
#         if hasattr(args[0], "class_type") and args[0].class_type == "XsdString":
#             return args[0]
#         else:
#             if isinstance(args[0], dict):
#                 new_args = (args[0].pop('value'), )
#                 kwargs.update(args[0])
#             else:
#                 new_args = args
#             if "lang" in kwargs.keys():
#                 lang = kwargs.pop("lang")
#             else:
#                 lang = None
#             newobj = str.__new__(cls, *new_args, **kwargs)
#             newobj.lang = lang
#             newobj.value = str(new_args[0])
#         return newobj

#     def __init__(self, *args, **kwargs):
#         pass

#     def __repr__(self):
#         return self._format(method="sparql")

#     def __add__(self, other):
#         if hasattr(other, "datatype"):
#             rtn_lang = None
#             if other.datatype == "xsd:string":
#                 rtn_val = self.value + other.value
#                 if other.lang and self.lang and other.lang != self.lang:
#                     rtn_lang = None
#                 elif other.lang:
#                     rtn_lang = other.lang
#                 else:
#                     rtn_lang = self.lang
#             else:
#                 rtn_val = self.value + str(other.value)
#         else:
#             rtn_val = self.value + str(other)
#             rtn_lang = self.lang
#         return XsdString(rtn_val, lang=rtn_lang)

# class XsdBoolean(BaseRdfDataType):
#     """ Boolean instance of rdf xsd:boolean type value"""

#     datatype = Uri("xsd:boolean")
#     class_type = "XsdBoolean"
#     py_type = bool
#     es_type = "boolean"

#     def __init__(self, value):
#         if hasattr(value, "class_type") and value.class_type == "XsdBoolean":
#             self.value = bool(self.value)
#         else:
#             self.value = cbool(str(value))

#     def __eq__(self, value):
#         if value == self.value:
#             return True
#         elif value != self.value:
#             return False

#     def __bool__(self):
#         #pdb.set_trace()
#         if self.value is None:
#             return False
#         return self.value

# class XsdDate(date, BaseRdfDataType):
#     """ Datetime Date instacne of rdf xsd:date type value"""

#     datatype = Uri("xsd:date")
#     class_type = "XsdDate"
#     py_type = date
#     es_type = "date"
#     es_format = "strict_date_optional_time||epoch_millis"

#     def __new__(cls, *args, **kwargs):
#         if hasattr(args[0], "class_type") and args[0].class_type == "XsdDate":
#             return args[0]
#         else:
#             yy = args[0]
#             mm = args[1:2][0] if args[1:2] else 0
#             dd = args[2:3][0] if args[2:3] else 0
#             if isinstance(args[0], str):
#                 yy = parse(args[0])
#             if isinstance(yy, date) or isinstance(yy, datetime):
#                 dd = yy.day
#                 mm = yy.month
#                 yy = yy.year
#         return date.__new__(cls, yy, mm, dd, **kwargs)

#     def __init__(self, *args, **kwargs):
#         self.value = self

# class XsdDatetime(datetime, BaseRdfDataType):
#     """ Datetime Datetime instance of rdf xsd:datetime type value"""

#     datatype = Uri("xsd:dateTime")
#     class_type = "XsdDateTime"
#     py_type = datetime
#     es_type = "date"
#     es_format = "strict_date_optional_time||epoch_millis"

#     def __new__(cls, *args, **kwargs):
#         if hasattr(args[0], "class_type") and \
#                 args[0].class_type == "XsdDatetime":
#             return args[0]
#         else:
#             yy = args[0]
#             mm = args[1:2][0] if args[1:2] else 0
#             dd = args[2:3][0] if args[2:3] else 0
#             hh = args[3:4][0] if args[3:4] else 0
#             mi = args[4:5][0] if args[4:5] else 0
#             ss = args[5:6][0] if args[5:6] else 0
#             ms = args[6:7][0] if args[6:7] else 0
#             tz = args[7:8][0] if args[7:8] else timezone.utc
#             if isinstance(args[0], str):
#                 yy = parse(args[0])
#             if isinstance(yy, datetime):
#                 tz = yy.tzinfo if yy.tzinfo else timezone.utc
#                 ms = yy.microsecond
#                 ss = yy.second
#                 mi = yy.minute
#             if isinstance(yy, date) or isinstance(yy, datetime):
#                 hh = yy.hour
#                 dd = yy.day
#                 mm = yy.month
#                 yy = yy.year
#             vals = tuple([yy, mm, dd, hh, mi, ss, ms, tz])
#         return datetime.__new__(cls, *vals, **kwargs)

#     def __init__(self, *args, **kwargs):
#         self.value = self

# class XsdTime(time, BaseRdfDataType):
#     """ Datetime Datetime instance of rdf xsd:datetime type value"""

#     datatype = Uri("xsd:time")
#     class_type = "XsdTime"
#     py_type = time

#     def __new__(cls, *args, **kwargs):
#         if hasattr(args[0], "class_type") and \
#                 args[0].class_type == "XsdTime":
#             return args[0]
#         else:
#             hh = args[0]
#             mi = args[1:2][0] if args[1:2] else 0
#             ss = args[2:3][0] if args[2:3] else 0
#             ms = args[3:4][0] if args[3:4] else 0
#             tz = args[4:5][0] if args[4:5] else timezone.utc
#             if isinstance(args[0], str):
#                 hh = parse(args[0])
#             if isinstance(hh, datetime) or isinstance(hh, time):
#                 tz = hh.tzinfo if hh.tzinfo else timezone.utc
#                 ms = hh.microsecond
#                 ss = hh.second
#                 mi = hh.minute
#                 hh = hh.hour
#             vals = tuple([hh, mi, ss, ms, tz])
#         return time.__new__(cls, *vals, **kwargs)

#     def __init__(self, *args, **kwargs):
#         self.value = self

# class XsdInteger(int, BaseRdfDataType):
#     """ Integer instance of rdf xsd:string type value"""

#     datatype = Uri("xsd:integer")
#     class_type = "XsdInteger"
#     py_type = int
#     es_type = "long"

#     def __new__(cls, *args, **kwargs):
#         if hasattr(args[0], "class_type") and \
#                 args[0].class_type == "XsdInteger":
#             return args[0]
#         else:
#             newobj = int.__new__(cls, *args, **kwargs)
#         return newobj

#     def __init__(self, *args, **kwargs):
#         self.value = int(self)

#     def __repr__(self):
#         return self._format(method="sparql")

#     def _internal_add(self, other):
#         """ Used for specifing addition methods for
#            __add__, __iadd__, __radd__
#         """
#         if hasattr(other, "datatype"):
#             if other.datatype == self.datatype:
#                 rtn_val = self.value + other.value
#             else:
#                 rtn_val = self.value + int(other.value)
#         else:
#             rtn_val = self.value + other
#         return XsdInteger(rtn_val)

#     def _internal_sub(self, other, method=None):
#         """ Used for specifing addition methods for
#            __add__, __iadd__, __radd__
#         """
#         if hasattr(other, "datatype"):
#             if other.datatype == self.datatype:
#                 oval = other.value
#             else:
#                 oval = int(other.value)
#         else:
#             oval = int(other)
#         if method == 'rsub':
#             rtn_val = oval - self.value
#         else:
#             rtn_val = self.value - oval
#         return XsdInteger(rtn_val)

#     def __add__(self, other):
#         return self._internal_add(other)

#     def __iadd__(self, other):
#         return self._internal_add(other)

#     def __radd__(self, other):
#         return self._internal_add(other)

#     def __sub__(self, other):
#         return self._internal_sub(other)

#     def __isub__(self, other):
#         return self._internal_sub(other)

#     def __rsub__(self, other):
#         return self._internal_sub(other, 'rsub')

# class XsdDecimal(Decimal, BaseRdfDataType):
#     """ Integer instance of rdf xsd:string type value"""

#     datatype = Uri("xsd:decimal")
#     class_type = "XsdDecimal"
#     py_type = int
#     es_type = "long"

#     def __new__(cls, *args, **kwargs):
#         if hasattr(args[0], "class_type") and \
#                 args[0].class_type == "XsdDecimal":
#             return args[0]
#         else:
#             vals = list(args)
#             vals[0] = str(args[0])
#             vals = tuple(vals)
#             newobj = Decimal.__new__(cls, *vals, **kwargs)
#         return newobj

#     def __init__(self, *args, **kwargs):
#         self.value = Decimal(str(self))

#     def __repr__(self):
#         return self._format(method="sparql")

#     def _internal_add(self, other):
#         """ Used for specifing addition methods for
#            __add__, __iadd__, __radd__
#         """
#         if hasattr(other, "datatype"):
#             if other.datatype == "xsd:decimal":
#                 rtn_val = self.value + Decimal(str(other.value))
#             else:
#                 rtn_val = self.value + Decimal(str(other.value))
#         else:
#             rtn_val = self.value + Decimal(str(other))
#         return XsdDecimal(str(float(rtn_val)))

#     def _internal_sub(self, other):
#         """ Used for specifing subtraction methods for
#            __sub__, __isub__, __rsub__
#         """
#         if hasattr(other, "datatype"):
#             if other.datatype == "xsd:decimal":
#                 rtn_val = self.value - Decimal(str(other.value))
#             else:
#                 rtn_val = self.value - Decimal(str(other.value))
#         else:
#             rtn_val = self.value - Decimal(str(other))
#         return XsdDecimal(str(float(rtn_val)))

#     def __add__(self, other):
#         return self._internal_add(other)

#     def __iadd__(self, other):
#         return self._internal_add(other)

#     def __radd__(self, other):
#         return self._internal_add(other)

#     def __sub__(self, other):
#         return self._internal_sub(other)

#     def __isub__(self, other):
#         return self._internal_sub(other)

#     def __rsub__(self, other):
#         return self._internal_sub(other)


# xsd_class_list = [Uri,
#                   BlankNode,
#                   XsdBoolean,
#                   XsdDate,
#                   XsdDatetime,
#                   XsdString,
#                   XsdTime,
#                   XsdInteger]

# DT_LOOKUP = {}
# for xsd_class in xsd_class_list:
#     attr_list = ["type", "py_type", "class_type"]
#     for attr in attr_list:
#         if hasattr(xsd_class, attr):
#             DT_LOOKUP[getattr(xsd_class, attr)] = xsd_class
#         elif hasattr(xsd_class, 'function') and \
#                 hasattr(xsd_class.function, attr):
#             DT_LOOKUP[getattr(xsd_class.function, attr)] = xsd_class
#     if hasattr(xsd_class, "datatype"):
#         DT_LOOKUP[xsd_class.datatype.sparql] = xsd_class
#         DT_LOOKUP[xsd_class.datatype.sparql_uri] = xsd_class
#         DT_LOOKUP[xsd_class.datatype.pyuri] = xsd_class
#         DT_LOOKUP[xsd_class.datatype.clean_uri] = xsd_class
#         DT_LOOKUP[xsd_class.datatype] = xsd_class
#     DT_LOOKUP[xsd_class] = xsd_class

# @functools.lru_cache(maxsize=None)
# def pyrdf(value, class_type=None, datatype=None, lang=None, **kwargs):
#     """ Coverts an input to one of the rdfdatatypes classes

#         Args:
#             value: any rdfdatatype, json dict or vlaue
#             class_type: "literal", "uri" or "blanknode"
#             datatype: "xsd:string", "xsd:int" , etc
#     """
#     if isinstance(value, BaseRdfDataType):
#         return value
#     elif isinstance(value, dict):
#         # test to see if the type is a literal, a literal will have a another
#         # dictionary key call datatype. Feed the datatype to the lookup to
#         # return the value else convert it to a XsdString
#         if value.get('type') == "literal":
#             if not value.get("datatype"):
#                 return XsdString(value['value'])
#             else:
#                 try:
#                     if value.get("lang"):
#                         # The lang keyword only applies to XsdString types
#                         return DT_LOOKUP[value['datatype']](value['value'],
#                                 lang=value.get("lang"))
#                     else:
#                         return DT_LOOKUP[value['datatype']](value['value'])
#                 except:
#                     rtn_val = BaseRdfDataType(value['value'])
#                     rtn_val.datatype = Uri(value['datatype'])
#                     return rtn_val
#         else:
#             return DT_LOOKUP[value['type']](value['value'])
#     else:
#         return DT_LOOKUP[type(value)](value['value'])
"""
#! To be implemented

"xsd_anyURI":
        # URI (Uniform Resource Identifier)
"xsd_base64Binary":
        # Binary content coded as "base64"
"xsd_byte":
        # Signed value of 8 bits
"xsd_decimal":
        # Decimal numbers
"xsd_double":
        # IEEE 64
"xsd_duration":
        # Time durations
"xsd_ENTITIES":
        # Whitespace
"xsd_ENTITY":
        # Reference to an unparsed entity
"xsd_float":
        # IEEE 32
"xsd_gDay":
        # Recurring period of time: monthly day
"xsd_gMonth":
        # Recurring period of time: yearly month
"xsd_gMonthDay":
        # Recurring period of time: yearly day
"xsd_gYear":
        # Period of one year
"xsd_gYearMonth":
        # Period of one month
"xsd_hexBinary":
        # Binary contents coded in hexadecimal
"xsd_ID":
        # Definition of unique identifiers
"xsd_IDREF":
        # Definition of references to unique identifiers
"xsd_IDREFS":
        # Definition of lists of references to unique identifiers
"xsd_int":
        # 32
"xsd_integer":
        # Signed integers of arbitrary length
"xsd_language":
        # RFC 1766 language codes
"xsd_long":
        # 64
"xsd_Name":
        # XML 1.O name
"xsd_NCName":
        # Unqualified names
"xsd_negativeInteger":
        # Strictly negative integers of arbitrary length
"xsd_NMTOKEN":
        # XML 1.0 name token (NMTOKEN)
"xsd_NMTOKENS":
        # List of XML 1.0 name tokens (NMTOKEN)
"xsd_nonNegativeInteger":
        # Integers of arbitrary length positive or equal to zero
"xsd_nonPositiveInteger":
        # Integers of arbitrary length negative or equal to zero
"xsd_normalizedString":
        # Whitespace
"xsd_NOTATION":
        # Emulation of the XML 1.0 feature
"xsd_positiveInteger":
        # Strictly positive integers of arbitrary length
"xsd_QName":
        # Namespaces in XML
"xsd_short":
        # 32
"xsd_string":
        # Any string
"xsd_time":
        # Point in time recurring each day
"xsd_token":
        # Whitespace
"xsd_unsignedByte":
        # Unsigned value of 8 bits
"xsd_unsignedInt":
        # Unsigned integer of 32 bits
"xsd_unsignedLong":
        # Unsigned integer of 64 bits
"xsd_unsignedShort":
        # Unsigned integer of 16 bits
"""


