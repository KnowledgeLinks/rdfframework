''' Application Configuration Manager '''
import inspect
import logging
import pdb 

from rdfframework.utilities import DictClass, make_class, pp

__author__ = "Mike Stabile, Jeremy Nelson"

MNAME = inspect.stack()[0][1]

class ConfigSingleton(type):
    """Singleton class for the RdfNsManager that will allow for only one
    instance of the RdfNsManager to be created. In addition the app config
    can be sent to the RdfNsManger even after instantiation so the the 
    default RDF namespaces can be loaded. """

    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(ConfigSingleton, 
                    cls).__call__(*args, **kwargs)
        else:
            if 'config' in kwargs:
                cls._instances[cls]._RdfConfigManager__load_config(kwargs['config'])
        return cls._instances[cls]


class RdfConfigManager(metaclass=ConfigSingleton):
    """ Extends the the rdflib Namespace Manager. Provides additional methods
    to easily generate prefixes in use thoughout the application 

    *** Of Note: this is a singleton class and only one instance of it will
    every exisit. """

    ln = "%s-RdfConfigManager" % MNAME
    log_level = logging.CRITICAL
    __type = 'DictClass'
    __reserved = ['dict', 
                 'get', 
                 'items', 
                 'keys', 
                 'values', 
                 '_RdfConfigManager__reserved',
                 '_DictClass__type',
                 'debug']

    def __init__(self, obj=None, start=True):
        self.__load_config(obj)

    def __load_config(self, obj, start=True):
        for attr in dir(self):
            if not attr.startswith("_") and attr not in self.__reserved:
                try:
                    delattr(self, attr)
                except:
                    pass
        if obj and start:
            new_class = DictClass(obj)
            for attr in dir(new_class):
                if not attr.startswith("_") and attr not in self.__reserved:
                    setattr(self, attr, getattr(new_class,attr))

    def __repr__(self):
        return "<%s.%s object at %s> (\n%s)" % (self.__class__.__module__,
                                         self.__class__.__name__,
                                         hex(id(self)),
                                         pp.pformat(DictClass(self).dict()))

    def __getattr__(self, attr):
        return None

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        else:
            return None

    def __str__(self):
        return str(self.dict())

    def __setattr__(self, attr, value):
        if isinstance(value, dict) or isinstance(value, list):
            value = DictClass(value)
        self.__dict__[attr] = value

    def dict(self):
        """ converts the class to a dictionary object """
        return DictClass(self).dict()


    def get(self, attr, none_val=None):
        if attr in self.keys():
            return getattr(self, attr)
        else:
            return none_val

    def keys(self):
        return [attr for attr in dir(self) if not attr.startswith("__") and \
                attr not in self.__reserved]

    def values(self):
        return [getattr(self, attr) for attr in dir(self) if not attr.startswith("__") and \
                attr not in self.__reserved]

    def items(self):
        return_list = []
        for attr in dir(self):
            if not attr.startswith("__") and attr not in self.__reserved:
                return_list.append((attr, getattr(self, attr)))
        return return_list