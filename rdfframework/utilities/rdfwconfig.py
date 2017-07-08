''' Application Configuration Manager '''
import inspect
import logging
import os
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
                cls._instances[cls]._RdfConfigManager__load_config(\
                        kwargs['config'])
                cls._instances[cls].is_initialized = True
        return cls._instances[cls]

def initialized(func):
    """ decorator for testing if the configmanager has been initialized
        prior to calling any attribute """

    def wrapper(self, *args, **kwargs):
        if not self.is_initialized:
            return "RdfConfigManager has not been initializied"
        else:
            return func(self, *args, **kwargs)
    return(wrapper)

class DictDot(dict):
    def __getattr__(self, value):
        return self[value]

class RdfConfigManager(metaclass=ConfigSingleton):
    """ Configuration Manager for the application. 

    *** Of Note: this is a singleton class and only one instance of it will
                 exisit. 
    """

    ln = "%s-RdfConfigManager" % MNAME
    log_level = logging.CRITICAL
    __type = 'DictClass'
    __reserved = ['dict', 
                 'get', 
                 'items', 
                 'keys', 
                 'values', 
                 '_RdfConfigManager__reserved',
                 'is_intialized',
                 '_DictClass__type',
                 'debug']
    is_initialized = False

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
        self.JSON_LOCATION = os.path.join(self.ROOT_FILE_PATH, 
                                          "json-definitions")
    
    @initialized
    def __repr__(self):
        return "<%s.%s object at %s> (\n%s)" % (self.__class__.__module__,
                                         self.__class__.__name__,
                                         hex(id(self)),
                                         pp.pformat(DictClass(self).dict()))
    
    @initialized
    def __getattr__(self, attr):
        return None
    
    @initialized
    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        else:
            return None
    
    @initialized
    def __str__(self):
        return str(self.dict())


    def __setattr__(self, attr, value, override=False):
        if override:
            pass
        elif isinstance(value, dict) or isinstance(value, list):
            value = DictClass(value)
        self.__dict__[attr] = value

    @initialized
    def dict(self):
        """ converts the class to a dictionary object """
        return DictClass(self).dict()

    @initialized
    def get(self, attr, none_val=None):
        if attr in self.keys():
            return getattr(self, attr)
        else:
            return none_val
    
    @initialized
    def keys(self):
        return [attr for attr in dir(self) if not attr.startswith("__") and \
                attr not in self.__reserved]
    
    @initialized
    def values(self):
        return [getattr(self, attr) for attr in dir(self) \
                if not attr.startswith("__") and attr not in self.__reserved]
    
    @initialized
    def items(self):
        return_list = []
        for attr in dir(self):
            if not attr.startswith("__") and attr not in self.__reserved:
                return_list.append((attr, getattr(self, attr)))
        return return_list