import os
import logging
import requests
import urllib
import datetime
import pdb

from dateutil.parser import parse as date_parse

from rdfframework.connections import ConnManager
from rdfframework.datatypes import RdfNsManager
from rdfframework.configuration import RdfConfigManager
from rdfframework.utilities import make_list
from .datamanager import DataFileManager

__CONNS__ = ConnManager()
__CFG__ = RdfConfigManager()
__NSM__ = RdfNsManager()


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
            if kwargs.get("conn"):
                cls._instances[cls].conn = kwargs['conn']
            if args:
                values = args[0]
            elif 'rdf_defs' in kwargs:
                values = kwargs['vocabularies']
            if values:
                cls._instances[cls].load(values, **kwargs)
        return cls._instances[cls]

    def __init__(self, *args, **kwargs):
        pass

    def clear(cls):
        cls._instances = {}

class DefinitionManager(DataFileManager, metaclass=DefManagerMeta):
    """
    RDF Vocabulary Manager. This class manages all of the RDF vocabulary
    for the rdfframework
    """
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
            "namespace": "http://www.w3.org/2006/vcard/ns#",
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
            "download": "http://id.loc.gov/ontologies/bibframe.rdf"
        }

    }

    def __init__(self, file_locations=[], conn=None, **kwargs):
        # add all namespaces to the RdfNsManager to ensure that there are no
        # conflicts with the config file
        [__NSM__.bind(prefix, val['namespace'], override=False, calc=False)
         for prefix, val in self.vocab_map.items()]
        self.conn = None
        if not conn:
            conn = kwargs.get("conn", __CONNS__.active_defs)
        if conn:
            super(DefinitionManager, self).__init__(file_locations,
                                                    conn,
                                                    **kwargs)
            if self.__file_locations__:
                self.load(self.__file_locations__, **kwargs)
        else:
            self.add_file_locations(file_locations)

    def __get_conn__(self, **kwargs):
        if not self.conn:
            self.conn = kwargs.get("conn", __CONNS__.active_defs)
        return kwargs.get("conn", self.conn)

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
        self.__set_cache_dir__(**kwargs)
        conn = self.__get_conn__(**kwargs)
        self.set_load_state(**kwargs)
        super(DefinitionManager, self).load(file_locations, **kwargs)
        if not file_locations:
            file_locations = self.__file_locations__
        if file_locations:
            log.info("loading vocabs into conn '%s'", conn)
        for item in file_locations:
            if item[0] == 'vocabularies':
                vocabs = item[1]
                if item[1] == "all":
                    vocabs = self.vocab_map
                for vocab in vocabs:
                    self.load_vocab(vocab)

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
        test_dirs = [self.vocab_dir] + cache_dirs
        try:
            test_dirs += [os.path.join(__CFG__.CACHE_DATA_PATH,
                                       "vocabularies")]
        except (RuntimeWarning, TypeError):
            pass
        super(DefinitionManager, self).__set_cache_dir__(test_dirs, **kwargs)

    def load_vocab(self, vocab_name, **kwargs):
        """ loads a vocabulary into the defintion triplestore

        args:
            vocab_name: the prefix, uri or filename of a vocabulary
        """
        log.setLevel(kwargs.get("log_level", self.log_level))

        vocab = self.get_vocab(vocab_name   , **kwargs)
        if vocab['filename'] in self.loaded:
            if self.loaded_times.get(vocab['filename'],
                    datetime.datetime(2001,1,1)).timestamp() \
                    < vocab['modified']:
                self.drop_file(vocab['filename'], **kwargs)
            else:
                return
        conn = kwargs.get("conn", self.conn)
        conn.load_data(graph=getattr(__NSM__.kdr, vocab['filename']).clean_uri,
                       data=vocab['data'],
                       datatype=vocab['filename'].split(".")[-1],
                       log_level=logging.WARNING)
        self.__update_time__(vocab['filename'], **kwargs)
        log.warning("\n\tvocab: '%s' loaded \n\tconn: '%s'",
                    vocab['filename'],
                    conn)
        self.loaded.append(vocab['filename'])

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

    def drop_vocab(self, vocab_name, **kwargs):
        """ Removes the vocab from the definiton triplestore

        args:
            vocab_name: the name or uri of the vocab to return

        """
        vocab_dict = self.__get_vocab_dict__(vocab_name, **kwargs)
        return self.drop_file(vocab_dict['filename'], **kwargs)

