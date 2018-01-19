import os
import inspect
import time
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
        is_writeable_dir

__CONNS__ = ConnManager()
__CFG__ = RdfConfigManager()
__NSM__ = RdfNsManager()

__MNAME__ = pyfile_path(inspect.stack()[0][1])

class DataFileManager():
    """ class for managing database connections """
    log_name = "%s:DataFileManager" % __MNAME__
    log_level = logging.INFO
    is_initialized = False

    def __init__(self, file_locations=[], conn=None, **kwargs):
        self.__file_locations__ = file_locations
        self.log_level = kwargs.get('log_level', self.log_level)
        if conn:
            kwargs['conn'] = conn
        self.conn = kwargs.get("conn", __CONNS__.datastore)
        self.__set_cache_dir__(**kwargs)
        self.__get_conn__(**kwargs)
        self.loaded = []
        self.loaded_files(**kwargs)
        self.loaded_times = self.load_times(**kwargs)
        if self.__file_locations__:
            self.load(self.__file_locations__, **kwargs)

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
        conn = self.__get_conn__(**kwargs)
        # pdb.set_trace()
        if self.loaded and not kwargs.get('reset', False):
            return self.loaded
        result = conn.query("""
                SELECT ?file
                {
                    {
                        SELECT DISTINCT ?g
                        {
                            graph ?g {?s ?p ?o} .
                            FILTER(?g!=<http://www.bigdata.com/rdf#nullGraph>
                                   && ?g!=kdr:load_times)
                        }
                    }
                    bind(REPLACE(str(?g) ,
                         "http://knowledgelinks.io/ns/data-resources/", "")
                         as ?file)
                }""")
        if result:
            self.loaded = [val['file']['value'] for val in result]
        else:
            self.loaded = result
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
        if file_locations:
            self.__file_locations__ += file_locations
        else:
            file_locations = self.__file_locations__
        conn = self.__get_conn__(**kwargs)
        for item in file_locations:
            if item[0] == 'directory':
                self.load_directory(item[1], **kwargs)
            elif item[0] == 'filepath':
                kwargs['is_file'] = True
                conn.load_data(item[1],**kwargs)
            elif item[0].startswith('package'):
                pkg_path = \
                        importlib.util.find_spec(\
                                item[1]).submodule_search_locations[0]
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
        test_dirs = cache_dirs
        try:
            test_dirs += [os.path.join(__CFG__.CACHE_DATA_PATH, "data")]
        except (RuntimeWarning, TypeError):
            pass
        cache_dir = None
        for directory in test_dirs:
            if is_writeable_dir(directory, mkdir=True):
                cache_dir = directory
                break
        self.cache_dir = cache_dir

    def load_file(self, filepath, **kwargs):
        """ loads a file into the defintion triplestore

        args:
            filepath: the path to the file
        """
        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
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
                       is_file=True,
                       log_level=logging.WARNING)
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
        """ removes the passed in file from the definition triplestore

        args:
            filename: the filename to remove
        """
        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
        log.setLevel(kwargs.get("log_level", self.log_level))
        conn = self.__get_conn__(**kwargs)
        result = conn.update_query("DROP GRAPH %s" % \
                                   getattr(__NSM__.kdr, filename),
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
        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
        log.setLevel(kwargs.get("log_level", self.log_level))
        conn = self.__get_conn__(**kwargs)
        result = conn.query("""
                SELECT ?file ?time
                {
                    graph kdr:load_times {?s ?p ?time} .
                    bind(REPLACE(str(?s),
                                 "http://knowledgelinks.io/ns/data-resources/",
                                 "")
                         as ?file)
                }""", **kwargs)
        return {item['file']['value']: XsdDatetime(item['time']['value'])
                for item in result}

    def load_directory(self, directory, **kwargs):
        """ loads all rdf files in a directory

        args:
            directory: full path to the directory
        """
        conn = self.__get_conn__(**kwargs)
        file_extensions = kwargs.get('file_extensions', conn.rdf_formats)
        file_list = list_files(directory,
                               file_extensions,
                               kwargs.get('include_subfolders', False),
                               include_root=True)
        for file in file_list:
            self.load_file(file[1], **kwargs)
