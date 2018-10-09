import logging
# import requests
# import urllib
# import datetime
# import pdb

# from dateutil.parser import parse as date_parse

from rdfframework.connections import ConnManager
# from rdfframework.datatypes import RdfNsManager
# from rdfframework.configuration import RdfConfigManager
# from rdfframework.utilities import make_list
from .datamanager import DataFileManager

__CONNS__ = ConnManager()

class DatastoreManagerMeta(type):
    """ Metaclass ensures that there is only one instance manager
    """

    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(DatastoreManagerMeta,
                                        cls).__call__(*args, **kwargs)
        else:
            values = None
            if kwargs.get("conn"):
                cls._instances[cls].conn = kwargs['conn']
            if args:
                values = args[0]
            if values:
                cls._instances[cls].load(values, **kwargs)
        return cls._instances[cls]

    def __init__(self, *args, **kwargs):
        pass

    def clear(cls):
        cls._instances = {}

class DatastoreManager(DataFileManager, metaclass=DatastoreManagerMeta):
    """
    Datastore file manager. This class manages all of the RDF vocabulary
    for the rdfframework
    """
    log_level = logging.INFO
    is_initialized = False

    def __init__(self, file_locations=[], conn=None, **kwargs):
        self.conn = None
        if not conn:
            conn = kwargs.get("conn", __CONNS__.datastore)
        if conn:
            super(DatastoreManager, self).__init__(file_locations,
                                                   conn,
                                                   **kwargs)
            if self.__file_locations__:
                self.load(self.__file_locations__, **kwargs)
        else:
            self.add_file_locations(file_locations)
