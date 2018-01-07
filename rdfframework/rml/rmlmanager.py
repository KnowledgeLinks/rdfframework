''' Manager for managing application wide RML Maps '''
import os
import types
import inspect
import logging
import json

from rdfframework.configuration import RdfConfigManager
from rdfframework.utilities import pyfile_path, pick
from rdfframework.sparql import get_graph
from rdfframework.datasets import RdfDataset
from rdfframework.datatypes import RdfNsManager

__author__ = "Mike Stabile, Jeremy Nelson"

# set the modulename
MNAME = pyfile_path(inspect.stack()[0][1])
CFG = RdfConfigManager()
NSM = RdfNsManager()

class RmlSingleton(type):
    """Singleton class that will allow for only one instance to be created.
    """
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(RmlSingleton,
                    cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class RmlManager(metaclass=RmlSingleton):
    """ Creates a Singleton Manger for loading Rml Maps"""

    ln = "%s-RmlManager" % MNAME
    log_level = logging.DEBUG

    def __init__(self, conn=None, cache_dir=None, **kwargs):
        args = []
        super(RmlManager, self).__init__(*args, **kwargs)
        self.rml_maps = {}
        self.conn = pick(conn, CFG.rml_tstore)
        self.cache_dir = pick(cache_dir,
                              os.path.join(CFG.CACHE_DATA_PATH, 'rml_files'))

    def load_rml(self, rml_name):
        """ loads an rml mapping into memory

        args:
            rml_name(str): the name of the rml file
        """
        conn = self.conn
        cache_path = os.path.join(self.cache_dir, rml_name)
        if not os.path.exists(cache_path):
            results = get_graph(NSM.uri(getattr(NSM.kdr, rml_name), False),
                                conn)
            if not results:
                raise AttributeError("There is no mapping data for '%s'" % rml_name)
            with open(cache_path, "w") as file_obj:
                file_obj.write(json.dumps(results, indent=4))
        else:
            results = json.loads(open(cache_path).read())

        self[rml_name] = RdfDataset(results)
        return self[rml_name]

    def get_rml(self, rml_name):
        """ returns the rml mapping RdfDataset

        rml_name(str): Name of the rml mapping to retrieve
        """

        try:
            return self.rml_maps[rml_name]
        except KeyError:
            return self.load_rml(rml_name)

    def del_rml(self, rml_name):
        """ deletes an rml mapping from memory"""
        try:
            del self.rml_maps[rml_name]
        except KeyError:
            pass

    def __getitem__(self, key):
        return self.get_rml(key)

    def list_maps(self):
        """ Returns a list of loaded rml mappings """
        return list(self.rml_maps)
