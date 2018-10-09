''' Manager for managing application wide RML Maps '''
import os
import types
import inspect
import logging
import json
import importlib
import pdb

from rdfframework.configuration import RdfConfigManager
from rdfframework.utilities import pyfile_path, pick, list_files
from rdfframework.sparql import get_graph
from rdfframework.datasets import RdfDataset
from rdfframework.datatypes import RdfNsManager


__author__ = "Mike Stabile, Jeremy Nelson"

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

    log_level = logging.DEBUG
    rdf_formats = ['xml', 'rdf', 'ttl', 'gz', 'nt']
    def __init__(self, conn=None, cache_dir=None, **kwargs):
        args = []
        super(RmlManager, self).__init__(*args, **kwargs)
        self.rml_maps = {}
        self.processors = {}

    def register_defs(self, def_list, **kwargs):
        """
        Registers a list of Rml defintions objects

        Args:
        -----
            def_list: list of objects defining the rml definitons
        """
        for item in def_list:
            if isinstance(item, tuple):
                self.register_rml_def(*item, **kwargs)
            elif isinstance(item, dict):
                cp_kwargs = kwargs.copy()
                item.update(kwargs)
                self.register_rml_def(**item)

    def register_rml_def(self,
                         location_type,
                         location,
                         filename=None,
                         **kwargs):
        """
        Registers the rml file locations for easy access

        Args:
        -----
            location_type: ['package_all',
                            'package_file',
                            'directory',
                            'filepath']
            location: The correlated location string based on the location_type
            filename: Optional, associated with 'package_file' location_type

        kwargs:
        -------
            include_subfolders: Boolean
        """
        if location_type == 'directory':
            self.register_directory(location, **kwargs)
        elif location_type == 'filepath':
            if not os.path.exists(location):
                raise OSError("File not found", location)
            if os.path.isfile(location):
                self.register_rml(location)
            elif filename:
                new_loc = os.path.join(location, filename)
                if not os.path.exists(new_loc):
                    raise OSError("File not found", new_loc)
                elif os.path.isfile(new_loc):
                    self.register_rml(new_loc)
            else:
                raise OSError("File not found", location)
        elif location_type.startswith('package'):
            pkg_path = \
                    importlib.util.find_spec(\
                            location).submodule_search_locations[0]
            if location_type.endswith('_all'):
                self.register_directory(pkg_path, **kwargs)
            elif location_type.endswith('_file'):
                filepath = os.path.join(pkg_path, filename)
                self.register_rml(filepath, **kwargs)
            else:
                raise NotImplementedError

    def register_rml(self, filepath, **kwargs):
        """
        Registers the filepath for an rml mapping

        Args:
        -----
            filepath: the path the rml file
        """
        name = os.path.split(filepath)[-1]
        if name in self.rml_maps and self.rml_maps[name] != filepath:
            raise Exception("RML name already registered. Filenames must be "
                            "unique.",
                            (self.rml_maps[name], filepath))
        self.rml_maps[name] = filepath

    def register_directory(self, dirpath, **kwargs):
        """
        Registers all of the files in the the directory path
        """

        kwargs['file_extensions'] = kwargs.get("file_extensions",
                                               self.rdf_formats)
        files = list_files(file_directory=dirpath, **kwargs)
        for fileinfo in files:
            self.register_rml(fileinfo[-1], **kwargs)

    def make_processor(self, name, mappings, processor_type, **kwargs):
        """
        Instantiates a RmlProcessor and registers it in the manager

        Args:
        -----
            name: the name to register the processor
            mappings: the list RML mapping definitions to use
            processor_type: the name of the RML processor to use
        """
        from .processor import Processor
        if self.processors.get(name):
            raise LookupError("processor has already been created")
        if isinstance(mappings, list):
            mappings = [self.get_rml(item) for item in mappings]
        else:
            mappings = [self.get_rml(mappings)]
        self.processors[name] = Processor[processor_type](mappings, **kwargs)
        self.processors[name].name = name
        return self.processors[name]

    def get_processor(self,
                      name,
                      mappings=None,
                      processor_type=None,
                      **kwargs):
        """
        Returns the specified RML Processor
        """
        try:
            return self.processors[name]
        except KeyError:
            return  self.make_processor(name,
                                        mappings,
                                        processor_type,
                                        **kwargs)


    # def load_rml(self, rml_name):
    #     """ loads an rml mapping into memory

    #     args:
    #         rml_name(str): the name of the rml file
    #     """
    #     conn = self.conn
    #     cache_path = os.path.join(self.cache_dir, rml_name)
    #     if not os.path.exists(cache_path):
    #         results = get_graph(NSM.uri(getattr(NSM.kdr, rml_name), False),
    #                             conn)
    #         if not results:
    #             raise AttributeError("There is no mapping data for '%s'" % \
    #                                  rml_name)
    #         with open(cache_path, "w") as file_obj:
    #             file_obj.write(json.dumps(results, indent=4))
    #     else:
    #         results = json.loads(open(cache_path).read())

    #     self[rml_name] = RdfDataset(results)
    #     return self[rml_name]

    def get_rml(self, rml_name, rtn_format="filepath"):
        """ returns the rml mapping filepath

        rml_name(str): Name of the rml mapping to retrieve
        rtn_format: ['filepath', 'data']
        """

        try:
            rml_path = self.rml_maps[rml_name]
        except KeyError:
            if rml_name in self.rml_maps.values() or os.path.exists(rml_name):
                rml_path = rml_name
            else:
                raise LookupError("rml_name '%s' is not registered" % rml_name)
        if rtn_format == "data":
            with open(rml_path, "rb") as fo:
                return fo.read()
        return rml_path

    def del_rml(self, rml_name):
        """ deletes an rml mapping from memory"""
        try:
            del self.rml_maps[rml_name]
        except KeyError:
            pass

    def __getitem__(self, key):
        return self.get_rml(key)

    @property
    def list_maps(self):
        """ Returns a list of loaded rml mappings """
        return list(self.rml_maps)
