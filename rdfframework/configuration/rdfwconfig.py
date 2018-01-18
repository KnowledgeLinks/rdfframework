''' Application Configuration Manager '''
import inspect
import os
import logging
import pdb

from elasticsearch import Elasticsearch
from rdfframework.utilities import DictClass, pp, initialized, pyfile_path


__author__ = "Mike Stabile, Jeremy Nelson"

MNAME = pyfile_path(inspect.stack()[0][1])

class ConfigSingleton(type):
    """Singleton class for the RdfConfigManager that will allow for only one
    instance of the RdfConfigManager to be created.  """

    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(ConfigSingleton,
                                        cls).__call__(*args, **kwargs)
        else:
            config = None
            if args:
                config = args[0]
            elif 'config' in kwargs:
                config = kwargs['config']
            if config:
                cls._instances[cls]._RdfConfigManager__load_config(config) # pylint: disable=W0212
        return cls._instances[cls]

    def clear(cls):
        cls._instances = {}


class RdfConfigManager(metaclass=ConfigSingleton):
    """ Configuration Manager for the application.

    *** Of Note: this is a singleton class and only one instance of it will
                 exisit.
    """

    log_name = "%s-RdfConfigManager" % MNAME
    log_level = logging.INFO
    __type = 'DictClass'
    __reserved = ['dict',
                  'get',
                  'items',
                  'keys',
                  'values',
                  '_RdfConfigManager__reserved',
                  'is_intialized',
                  '_DictClass__type',
                  'debug',
                  'os']
    is_initialized = False
    locked = False

    def __init__(self, config=None):
        if config:
            self.__load_config(config)

    def __load_config(self, obj):
        """ Reads a python config file and adds that values as attributes to
            the class

            args:
                obj: the config data
        """
        if self.is_initialized:
            raise ImportError("RdfConfigManager has already been initialized")

        for attr in dir(self):
            if not attr.startswith("_") and attr not in self.__reserved:
                try:
                    delattr(self, attr)
                except AttributeError:
                    pass
        if obj:
            new_class = DictClass(obj)
            for attr in dir(new_class):
                if not attr.startswith("_") and attr not in self.__reserved:
                    setattr(self, attr, getattr(new_class, attr))
        self.is_initialized = True
        self.__initialize_conns()
        self.__initialize_directories()


    def __make_tstore_conn(self, attr_name, params):
        """ Initializes a connection for a triplestore and sets that connection
            as paramater

            args:
                attr_name: The name the connection will be assigned in the
                    config manager
                params: The paramaters of the connection
        """

        from rdfframework.connections import make_tstore_conn
        conn = make_tstore_conn(params)
        setattr(self, attr_name, conn)

    def __initialize_conns(self):
        """ Reads the loaded config and creates the defined database
            connections"""
        if self.get('DATA_TRIPLESTORE'):
            self.__make_tstore_conn('data_tstore', self.DATA_TRIPLESTORE)
        if self.get('DEFINITION_TRIPLESTORE'):
            self.__make_tstore_conn('def_tstore', self.DEFINITION_TRIPLESTORE)
        if self.get('RML_MAPS_TRIPLESTORE'):
            self.__make_tstore_conn('rml_tstore', self.RML_MAPS_TRIPLESTORE)
        if self.get('ES_URL'):
            setattr(self, 'es_conn', Elasticsearch([self.ES_URL]))

    def __initialize_directories(self):
        """ reads through the config and verifies if all directories exist and
            creates them if they do not """
        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
        log.setLevel(self.log_level)
        for attr in dir(self):
            if attr.endswith("_PATH"):
                path = getattr(self, attr)
                if path and not os.path.isdir(path):
                    log.warning("The '%s' --> '%s' directory does not exist. %s",
                             attr,
                             path,
                             "Creating directory!")
                    os.makedirs(path)

    def __repr__(self):
        if self.is_initialized:
            return "<%s.%s object at %s> (\n%s)" % (self.__class__.__module__,
                                                    self.__class__.__name__,
                                                    hex(id(self)),
                                                    pp.pformat( \
                                                    DictClass(self).dict()))
        else:
            return "<RdfConfigManager has not been initialized>"

    @initialized
    def __getattr__(self, attr):
        for key, value in self.__dict__.items():
            if attr.lower() == key.lower():
                return value
        return None

    @initialized
    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        return None

    @initialized
    def __str__(self):
        try:
            return str(self.dict())
        except TypeError:
            return ""

    def __setattr__(self, attr, value, override=False):
        if self.is_initialized and self.locked:
            raise RuntimeError("The configuration may not be changed after" + \
                               " locking")
        if str(attr) in self.__reserved:
            raise AttributeError("'%s' is a reserved word in this class." % \
                                 attr)
        if not self.is_initialized and isinstance(value, (list, dict)):
            value = DictClass(value)
        self.__dict__[attr] = value

    @initialized
    def dict(self):
        """ converts the class to a dictionary object """
        return DictClass(self).dict()

    @initialized
    def get(self, attr, none_val=None):
        """ returns and attributes value or a supplied default

            args:
                attr: the attribute name
                none_val: the value to return in the attribute is not found or
                        is equal to 'None'.
        """
        if attr in self.keys():
            return getattr(self, attr)
        return none_val

    @initialized
    def keys(self):
        """ returns a list of the attributes in the config manager """
        return [attr for attr in dir(self) if not attr.startswith("_") and \
                attr not in self.__reserved]

    @initialized
    def values(self):
        """ returns the values of the config manager """
        return [getattr(self, attr) for attr in dir(self) \
                if not attr.startswith("_") and attr not in self.__reserved]

    @initialized
    def items(self):
        """ returns a list of tuples with the in a key: value combo of the
        config manager """
        return_list = []
        for attr in dir(self):
            if not attr.startswith("_") and attr not in self.__reserved:
                return_list.append((attr, getattr(self, attr)))
        return return_list

    # def __del__(self):
    #     try:
    #         print ("deleting ", self)
    #     except TypeError:
    #         print ("deleting RdfConfigManager")
    #     except:
    #         pdb.set_trace()
