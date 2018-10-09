import os
import inspect
import time
import copy
import logging
import requests
# import tempfile
import errno
import pdb
import urllib
import datetime
import importlib

from dateutil.parser import parse as date_parse

from rdfframework.connections import ConnManager
from rdfframework.datatypes import RdfNsManager, XsdDatetime, pyrdf
from rdfframework.configuration import RdfConfigManager
from rdfframework.utilities import pyfile_path, make_list, list_files, \
        is_writable_dir

__CONNS__ = ConnManager()
__CFG__ = RdfConfigManager()
__NSM__ = RdfNsManager()


class DataFileManager():
    """ class for managing database connections """
    log_level = logging.INFO
    is_initialized = False

    def __init__(self, file_locations=[], conn=None, **kwargs):
        self.add_file_locations(file_locations)
        self.log_level = kwargs.get('log_level', self.log_level)
        if conn:
            kwargs['conn'] = conn
        self.conn = conn
        self.__set_cache_dir__(**kwargs)
        self.__get_conn__(**kwargs)
        self.set_load_state(**kwargs)
        if self.__file_locations__:
            self.load(self.__file_locations__, **kwargs)

    def set_load_state(self, **kwargs):
        """
        Reads database to get loaded file times
        """
        self.load_times(**kwargs)

    def add_file_locations(self, file_locations=[]):
        """
        Adds a list of file locations to the current list

        Args:
            file_locations: list of file location tuples
        """
        if not hasattr(self, '__file_locations__'):
            self.__file_locations__ = copy.copy(file_locations)
        else:
            self.__file_locations__ += copy.copy(file_locations)


    def reset(self, **kwargs):
        """ Reset the triplestore with all of the data
        """
        self.drop_all(**kwargs)
        file_locations = self.__file_locations__
        self.__file_locations__ = []
        self.load(file_locations, **kwargs)

    def __get_conn__(self, **kwargs):
        if not self.conn:
            self.conn = kwargs.get("conn", __CONNS__.datastore)
        return kwargs.get("conn", self.conn)

    def drop_all(self, **kwargs):
        """ Drops all definitions"""
        conn = self.__get_conn__(**kwargs)
        conn.update_query("DROP ALL")
        self.loaded = []
        self.loaded_times = {}

    def loaded_files(self, **kwargs):
        """ returns a list of loaded definition files """
        # self.loaded = list(self.load_times(**kwargs))
        return self.loaded

    def load(self, file_locations=[], **kwargs):
        """ Loads the file_locations into the triplestores

        args:
            file_locations: list of tuples to load
                    [('vocabularies', [list of vocabs to load])
                     ('directory', '/directory/path')
                     ('filepath', '/path/to/a/file')
                     ('package_all', 'name.of.a.package.with.defs')
                     ('package_file','name.of.package', 'filename')]
            custom: list of custom definitions to load
        """
        self.set_load_state(**kwargs)
        if file_locations:
            self.__file_locations__ += file_locations
        else:
            file_locations = self.__file_locations__
        conn = self.__get_conn__(**kwargs)
        if file_locations:
            log.info("Uploading files to conn '%s'", conn)
        for item in file_locations:
            log.info("loading '%s", item)
            if item[0] == 'directory':
                self.load_directory(item[1], **kwargs)
            elif item[0] == 'filepath':
                kwargs['is_file'] = True
                self.load_file(item[1],**kwargs)
            elif item[0].startswith('package'):
                log.info("package: %s\nspec: %s",
                         item[1],
                         importlib.util.find_spec(item[1]))
                try:
                    pkg_path = \
                            importlib.util.find_spec(\
                                    item[1]).submodule_search_locations[0]
                except TypeError:
                    pkg_path = importlib.util.find_spec(item[1]).origin
                    pkg_path = os.path.split(pkg_path)[0]
                if item[0].endswith('_all'):
                    self.load_directory(pkg_path, **kwargs)
                elif item[0].endswith('_file'):
                    filepath = os.path.join(pkg_path, item[2])
                    self.load_file(filepath, **kwargs)
                else:
                    raise NotImplementedError
        self.loaded_files(reset=True)
        self.loaded_times = self.load_times(**kwargs)


    def __set_cache_dir__(self, cache_dirs=[], **kwargs):
        """ sets the cache directory by test write permissions for various
        locations

        args:
            directories: list of directories to test. First one with read-write
                    permissions is selected.
        """
        # add a path for a subfolder 'vocabularies'
        log.setLevel(kwargs.get("log_level", self.log_level))
        log.debug("setting cache_dir")
        test_dirs = cache_dirs
        try:
            test_dirs += [__CFG__.dirs.data]
        except (RuntimeWarning, TypeError):
            pass
        cache_dir = None
        for directory in test_dirs:
            try:
                if is_writable_dir(directory, mkdir=True):
                    cache_dir = directory
                    break
            except TypeError:
                pass
        self.cache_dir = cache_dir
        log.debug("cache dir set as: '%s'", cache_dir)
        log.setLevel(self.log_level)

    def load_file(self, filepath, **kwargs):
        """ loads a file into the defintion triplestore

        args:
            filepath: the path to the file
        """
        log.setLevel(kwargs.get("log_level", self.log_level))
        filename = os.path.split(filepath)[-1]
        if filename in self.loaded:
            if self.loaded_times.get(filename,
                    datetime.datetime(2001,1,1)).timestamp() \
                    < os.path.getmtime(filepath):
                self.drop_file(filename, **kwargs)
            else:
                return
        conn = self.__get_conn__(**kwargs)
        conn.load_data(graph=getattr(__NSM__.kdr, filename).clean_uri,
                       data=filepath,
                       # log_level=logging.DEBUG,
                       is_file=True)
        self.__update_time__(filename, **kwargs)
        log.warning("\n\tfile: '%s' loaded\n\tconn: '%s'\n\tpath: %s",
                    filename,
                    conn,
                    filepath)
        self.loaded.append(filename)


    def __update_time__(self, filename, **kwargs):
        """ updated the mod time for a file saved to the definition_store

        Args:
            filename: the name of the file
        """
        conn = self.__get_conn__(**kwargs)
        load_time = XsdDatetime(datetime.datetime.utcnow())
        conn.update_query("""
                DELETE
                {{
                   GRAPH {graph} {{ ?file dcterm:modified ?val }}
                }}
                INSERT
                {{
                   GRAPH {graph} {{ ?file dcterm:modified {ctime} }}
                }}
                WHERE
                {{
                    VALUES ?file {{ kdr:{file} }} .
                    OPTIONAL {{
                        GRAPH {graph} {{?file dcterm:modified ?val }}
                    }}
                }}""".format(file=filename,
                             ctime=load_time.sparql,
                             graph="kdr:load_times"),
                **kwargs)
        self.loaded_times[filename] = load_time


    def drop_file(self, filename, **kwargs):
        """ removes the passed in file from the connected triplestore

        args:
            filename: the filename to remove
        """
        log.setLevel(kwargs.get("log_level", self.log_level))
        conn = self.__get_conn__(**kwargs)
        result = conn.update_query("DROP GRAPH %s" % \
                                   getattr(__NSM__.kdr, filename).sparql,
                                   **kwargs)
        # Remove the load time from the triplestore
        conn.update_query("""
                DELETE
                {{
                   GRAPH {graph} {{ ?file dcterm:modified ?val }}
                }}
                WHERE
                {{
                    VALUES ?file {{ kdr:{file} }} .
                    OPTIONAL {{
                        GRAPH {graph} {{?file dcterm:modified ?val }}
                    }}
                }}""".format(file=filename, graph="kdr:load_times"),
                **kwargs)
        self.loaded.remove(filename)
        log.warning("Dropped file '%s' from conn %s", filename, conn)
        return result


    def load_times(self, **kwargs):
        """ get the load times for the all of the definition files"""
        log.setLevel(kwargs.get("log_level", self.log_level))
        conn = self.__get_conn__(**kwargs)
        try:
            result = conn.query("""
                    SELECT ?file ?time
                    {
                        graph kdr:load_times {?s ?p ?time} .
                        bind(REPLACE(str(?s),
                            "http://knowledgelinks.io/ns/data-resources/",
                            "")
                             as ?file)
                    }""", **kwargs)
            loaded = {item['file']['value']: XsdDatetime(item['time']['value'])
                      for item in result}
            self.loaded = list(loaded)
            self.loaded_times = loaded
            log.setLevel(self.log_level)
            return loaded
        except requests.exceptions.ConnectionError:
            log.warning("connection error with '%s'", conn)
            log.setLevel(self.log_level)
            self.loaded = []
            return {}

    def load_directory(self, directory, **kwargs):
        """ loads all rdf files in a directory

        args:
            directory: full path to the directory
        """
        log.setLevel(kwargs.get("log_level", self.log_level))
        conn = self.__get_conn__(**kwargs)
        file_extensions = kwargs.get('file_extensions', conn.rdf_formats)
        file_list = list_files(directory,
                               file_extensions,
                               kwargs.get('include_subfolders', False),
                               include_root=True)
        for file in file_list:
            self.load_file(file[1], **kwargs)
        log.setLevel(self.log_level)


