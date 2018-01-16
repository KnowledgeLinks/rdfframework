import os
import inspect
import time
import logging
import requests
import tempfile
import errno
import pdb
import urllib
import datetime
import importlib

from dateutil.parser import parse as date_parse

from rdfframework.connections import ConnManager
from rdfframework.datatypes import RdfNsManager, XsdDatetime, pyrdf
from rdfframework.configuration import RdfConfigManager
from rdfframework.utilities import pyfile_path, make_list, list_files


__CONNS__ = ConnManager()
__CFG__ = RdfConfigManager()
__NSM__ = RdfNsManager()

__MNAME__ = pyfile_path(inspect.stack()[0][1])

class DefManagerMeta(type):
    """ Metaclass ensures that there is only one instance of the RdfConnManager
    """

    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(DefManagerMeta,
                                        cls).__call__(*args, **kwargs)
        else:
            values = None
            if args:
                values = args[0]
            elif 'rdf_defs' in kwargs:
                values = kwargs['vocabularies']
            if values:
                cls._instances[cls].load(values)
        return cls._instances[cls]

    def clear(cls):
        cls._instances = {}

class DefinitionManager(metaclass=DefManagerMeta):
    """ class for managing database connections """
    log_name = "%s:DefintionManager" % __MNAME__
    log_level = logging.INFO
    is_initialized = False
    vocab_dir = os.path.join(os.path.split(os.path.realpath(__file__))[0],
                             "vocabularies")
    vocab_map = {
        "rdf": {
            "filename": "rdf.ttl",
            "download": "https://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "namespace": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        },
        "owl": {
            "filename": "owl.ttl",
            "download": "http://www.w3.org/2002/07/owl#",
            "namespace": "http://www.w3.org/2002/07/owl#"
        },
        "schema": {
            "filename": "schema.nt",
            "download": "http://schema.org/version/latest/schema.nt",
            "namespace": "http://schema.org/"
        },
        "rdfs": {
            "filename": "rdfs.ttl",
            "download": "https://www.w3.org/2000/01/rdf-schema#",
            "namespace": "http://www.w3.org/2000/01/rdf-schema#"
        },
        "skos": {
            "filename": "skos.rdf",
            "namespace": "http://www.w3.org/2004/02/skos/core#",
            "download": "https://www.w3.org/2009/08/skos-reference/skos.rdf"
        },
        "dc": {
            "filename": "dc.ttl",
            "namespace": "http://purl.org/dc/elements/1.1/",
            "download": ["http://purl.org/dc/elements/1.1/",
                         "http://dublincore.org/2012/06/14/dcelements"]
        },
        "dcterm": {
            "filename": "dcterm.ttl",
            "download": ["http://purl.org/dc/terms/",
                         "http://dublincore.org/2012/06/14/dcterms"],
            "namespace": "http://purl.org/dc/terms/"
        },
        "void": {
            "filename": "void.ttl",
            "namespace": "http://rdfs.org/ns/void#",
            "download": "http://vocab.deri.ie/void.ttl"
        },
        "adms": {
            "filename": "adms.ttl",
            "namespace": "https://www.w3.org/ns/adms#",
            "download": "https://www.w3.org/ns/adms#"
        },
        "vcard": {
            "filename": "vcard.ttl",
            "namespace": "https://www.w3.org/2006/vcard/ns#",
            "download": "https://www.w3.org/2006/vcard/ns#"
        },
        "foaf": {
            "filename": "foaf.rdf",
            "namespace": "http://xmlns.com/foaf/0.1/",
            "download": "http://xmlns.com/foaf/spec/20140114.rdf"
        },
        "bf": {
            "filename": "bf.rdf",
            "namespace": "http://id.loc.gov/ontologies/bibframe/",
            "download": "http://bibframe.org/vocab.rdf"
        }

    }

    def __init__(self, rdf_defs=[], **kwargs):
        self.__rdf_defs__ = rdf_defs
        self.__custom__ = {}
        self.log_level = kwargs.get('log_level', self.log_level)
        self.__set_cache_dir__(**kwargs)
        self.loaded = []
        self.loaded_files(**kwargs)
        self.loaded_times = self.load_times(**kwargs)
        # add all namespaces to the RdfNsManager to ensure that there are no
        # conflicts with the config file
        [__NSM__.bind(prefix, val['namespace'], override=False, calc=False)
         for prefix, val in self.vocab_map.items()]
        if self.__rdf_defs__:
            self.load(self.__rdf_defs__, **kwargs)

    def reset(self, **kwargs):
        """ Reset the defintion store with all of the vocabularies
        """
        self.drop_all(**kwargs)
        rdf_defs = self.__rdf_defs__
        self.__rdf_defs__ = []
        self.load(rdf_defs, **kwargs)

    def drop_all(self, **kwargs):
        """ Drops all definitions"""
        conn = kwargs.get("conn", __CONNS__.active_defs)
        conn.update_query("DROP ALL")
        self.loaded = []
        self.loaded_times = {}

    def loaded_files(self, **kwargs):
        """ returns a list of loaded definition files """
        conn = kwargs.get("conn", __CONNS__.active_defs)
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
                            FILTER(?g!=bd:nullGraph&&?g!=kdr:load_times)
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

    def load(self, rdf_defs=[], **kwargs):
        """ Loads the rdf_defs into the triplestores

        args:
            rdf_defs: list of tuples to load
                    [('vocabularies', [list of vocabs to load])
                     ('directory', '/directory/path')
                     ('filepath', '/path/to/a/file')
                     ('package_all', 'name.of.a.package.with.defs')
                     ('package_file','name.of.package', 'filename')]
            custom: list of custom definitions to load
        """
        if rdf_defs:
            self.__rdf_defs__ += rdf_defs
        else:
            rdf_defs = self.__rdf_defs__
        conn = kwargs.get("conn", __CONNS__.active_defs)
        for item in rdf_defs:
            if item[0] == 'directory':
                self.load_directory(item[1], **kwargs)
            elif item[0] == 'filepath':
                kwargs['is_file'] = True
                conn.load_data(item[1],**kwargs)
            elif item[0] == 'vocabularies':
                vocabs = item[1]
                if item[1] == "all":
                    vocabs = self.vocab_map
                for vocab in vocabs:
                    self.load_vocab(vocab)
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
        test_dirs = [self.vocab_dir] + \
                    cache_dirs + \
                    [os.path.join(__CFG__.CACHE_DATA_PATH, "vocabularies")]
        cache_dir = None
        for directory in test_dirs:
            if is_writeable_dir(directory, mkdir=True):
                cache_dir = directory
                break
        self.cache_dir = cache_dir

    def load_vocab(self, vocab_name, **kwargs):
        """ loads a vocabulary into the defintion triplestore

        args:
            vocab_name: the prefix, uri or filename of a vocabulary
        """
        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
        log.setLevel(kwargs.get("log_level", self.log_level))

        vocab = self.get_vocab(vocab_name   , **kwargs)
        if vocab['filename'] in self.loaded:
            if self.loaded_times.get(vocab['filename'],
                    datetime.datetime(2001,1,1)).timestamp() \
                    < vocab['modified']:
                self.drop_file(vocab['filename'], **kwargs)
            else:
                return
        conn = kwargs.get("conn", __CONNS__.active_defs)
        conn.load_data(graph=getattr(__NSM__.kdr, vocab['filename']).clean_uri,
                       data=vocab['data'],
                       datatype=vocab['filename'].split(".")[-1],
                       log_level=logging.WARNING)
        self.__update_time__(vocab['filename'], **kwargs)
        log.warning("\n\tvocab: '%s' loaded \n\tconn: '%s'",
                    vocab['filename'],
                    conn)
        self.loaded.append(vocab['filename'])

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
        conn = kwargs.get("conn", __CONNS__.active_defs)
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
        conn = kwargs.get("conn", __CONNS__.active_defs)
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

    def __get_vocab_dict__(self, vocab_name, **kwargs):
        """ dictionary for the specified vocabulary

        args:
            vocab_name: the name or uri of the vocab to return
        """
        try:
            vocab_dict = self.vocab_map[vocab_name].copy()
        except KeyError:
            vocab_dict = {key: value for key, value in self.vocab_map.items()
                          if vocab_name in value.values()}
            vocab_name = list(vocab_dict)[0]
            vocab_dict = vocab_dict.pop(vocab_name)
        return vocab_dict

    def get_vocab(self, vocab_name, **kwargs):
        """ Returns data stream of an rdf vocabulary

        args:
            vocab_name: the name or uri of the vocab to return
        """
        vocab_dict = self.__get_vocab_dict__(vocab_name, **kwargs)

        filepaths = list(set([os.path.join(self.cache_dir,
                                           vocab_dict['filename']),
                              os.path.join(self.vocab_dir,
                                           vocab_dict['filename'])]))
        for path in filepaths:
            if os.path.exists(path):
                with open(path, 'rb') as f_obj:
                    vocab_dict.update({"name": vocab_name,
                                       "data": f_obj.read(),
                                       "modified": os.path.getmtime(path)})
                return vocab_dict
        download_locs = make_list(vocab_dict.get('download',[]))
        for loc in download_locs:

            loc_web = urllib.request.urlopen(loc)
            # loc_file_date = date_parse(loc_web.info()['Last-Modified'])
            urllib.request.urlretrieve(loc, filepaths[0])
            with open(filepaths[0], 'rb') as f_obj:
                vocab_dict.update({"name": vocab_name,
                                   "data": f_obj.read(),
                                   "modified": os.path.getmtime(filepaths[0])})
                return vocab_dict

    def drop_file(self, filename, **kwargs):
        """ removes the passed in file from the definition triplestore

        args:
            filename: the filename to remove
        """
        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
        log.setLevel(kwargs.get("log_level", self.log_level))
        conn = kwargs.get("conn", __CONNS__.active_defs)
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

    def drop_vocab(self, vocab_name, **kwargs):
        """ Removes the vocab from the definiton triplestore

        args:
            vocab_name: the name or uri of the vocab to return

        """
        vocab_dict = self.__get_vocab_dict__(vocab_name, **kwargs)
        return self.drop_file(vocab_dict['filename'], **kwargs)

    def load_times(self, **kwargs):
        """ get the load times for the all of the definition files"""
        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
        log.setLevel(kwargs.get("log_level", self.log_level))
        conn = kwargs.get("conn", __CONNS__.active_defs)
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

    def _set_datafiles(self):
        self.datafile_obj = {}

        if CFG.def_tstore:
            self._set_data_filelist(start_path=CFG.RDF_DEFINITION_FILE_PATH,
                                    attr_name='def_files',
                                    conn=CFG.def_tstore,
                                    file_exts=['ttl', 'nt', 'xml', 'rdf'],
                                    dir_filter=['rdfw-definitions', 'custom'])
        if CFG.rml_tstore:
            self._set_data_filelist(start_path=CFG.RML_DATA_PATH,
                                    attr_name='rml_files',
                                    conn=CFG.rml_tstore,
                                    file_exts=['ttl', 'nt', 'xml', 'rdf'])

    def load_directory(self, directory, **kwargs):
        """ loads all rdf files in a directory

        args:
            directory: full path to the directory
        """
        conn = kwargs.get("conn", __CONNS__.active_defs)
        file_extensions = kwargs.get('file_extensions', conn.rdf_formats)
        file_list = list_files(directory,
                               file_extensions,
                               kwargs.get('include_subfolders', False),
                               include_root=True)
        for file in file_list:
            self.load_file(file[1], **kwargs)

    # def _load_data(self, reset=False):
    #     ''' loads the RDF/turtle application data to the triplestore

    #     args:
    #         reset(bool): True will delete the definition dataset and reload
    #                 all of the datafiles.
    #     '''

    #     log = logging.getLogger("%s.%s" % (self.log_name,
    #                                        inspect.stack()[0][3]))
    #     log.setLevel(self.log_level)
    #     for attr, obj in self.datafile_obj.items():
    #         if reset or obj['latest_mod'] > obj['last_json_mod']:
    #             conn = obj['conn']
    #             sparql = "DROP ALL;"
    #             if os.path.isdir(obj['cache_path']):
    #                 shutil.rmtree(obj['cache_path'], ignore_errors=True)
    #             os.makedirs(obj['cache_path'])
    #             drop_extensions = conn.update_query(sparql)
    #             rdf_resource_templates = []
    #             rdf_data = []
    #             for path, files in obj['files'].items():
    #                 for file in files:
    #                     file_path = os.path.join(path, file)
    #                     result = conn.load_data(file_path,
    #                                             #datatype=data_type,
    #                                             graph=str(getattr(NSM.kdr,
    #                                                               file)),
    #                                             is_file=True)
    #                     if result.status_code > 399:
    #                         raise ValueError("Cannot load '{}' into {}".format(
    #                             file_name, conn))

    # def _set_data_filelist(self,
    #                        start_path,
    #                        attr_name,
    #                        conn,
    #                        file_exts=[],
    #                        dir_filter=set()):
    #     ''' does a directory search for data files '''

    #     def filter_path(filter_terms, dir_path):
    #         """ sees if any of the terms are present in the path if so returns
    #             True

    #         args:
    #             filter_terms(list): terms to check
    #             dir_path: the path of the directory
    #         """
    #         if filter_terms.intersection(set(dir_path.split(os.path.sep))):
    #             return True
    #         else:
    #             return False

    #     data_obj = {}
    #     files_dict = {}
    #     latest_mod = 0
    #     dir_filter = set(dir_filter)
    #     for root, dirnames, filenames in os.walk(start_path):
    #         if not dir_filter or filter_path(dir_filter, root):
    #             if file_exts:
    #                 filenames = [x for x in filenames
    #                              if x.split('.')[-1].lower() in file_exts]
    #             files_dict[root] = filenames
    #             for def_file in filenames:
    #                 file_mod = os.path.getmtime(os.path.join(root,def_file))
    #                 if file_mod > latest_mod:
    #                     latest_mod = file_mod
    #     data_obj['latest_mod'] = latest_mod
    #     data_obj['files'] = files_dict
    #     json_mod = 0
    #     cache_path = os.path.join(CFG.CACHE_DATA_PATH, attr_name)
    #     if cache_path:
    #         for root, dirnames, filenames in os.walk(cache_path):
    #             for json_file in filenames:
    #                 file_mod = os.path.getmtime(os.path.join(root,json_file))
    #                 if file_mod > json_mod:
    #                     json_mod = file_mod
    #     data_obj['last_json_mod'] = json_mod
    #     data_obj['conn'] = conn
    #     data_obj['cache_path'] = cache_path
    #     self.datafile_obj[attr_name] = data_obj

def is_writeable_dir(directory, **kwargs):
    """ tests to see if the directory is writable. If the directory does
        it can attempt to create it. If unable returns False

    args:
        directory: filepath to the directory

    kwargs:
        mkdir[bool]: create the directory if it does not exist

    returns
    """
    try:
        testfile = tempfile.TemporaryFile(dir = directory)
        testfile.close()
    except OSError as e:
        if e.errno == errno.EACCES:  # 13
            return False
        elif e.errno == errno.ENOENT: # 2
            if kwargs.get('mkdir') == True:
                try:
                    os.makedirs(directory)
                except OSError as e2:
                    if e2.errno == errno.EACCES: # 13
                        return False
            else:
                return False
        e.filename = directory
    return True
