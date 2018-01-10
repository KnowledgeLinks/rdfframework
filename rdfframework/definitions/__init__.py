import inspect
import time
import logging
import requests

from rdfframework.connections import ConnManager as conns

class DefManagerMeta(type):
    """ Metaclass ensures that there is only one instance of the RdfConnManager
    """

    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(ConnManagerMeta,
                                        cls).__call__(*args, **kwargs)
        else:
            values = None
            if args:
                values = args[0]
            elif 'vocabularies' in kwargs:
                values = kwargs['vocabularies']
            if conns:
                cls._instances[cls].load(values)
        return cls._instances[cls]

    def clear(cls):
        cls._instances = {}

class DefintionManager(metaclass=DefManagerMeta):
    """ class for managing database connections """
    log = "%s:DefintionManager" % __MNAME__
    log_level = logging.INFO
    is_initialized = False
    vocab_map = {
        "rdf": {
            "filename": "rdf.ttl",
            "download": "https://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "namespace": "https://www.w3.org/1999/02/22-rdf-syntax-ns#"
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
            "namespace": "https://www.w3.org/2000/01/rdf-schema#"
        },
        "skos": {
            "filename": "skos.rdf",
            "namespace": "http://www.w3.org/2004/02/skos/core#",
            "download": "https://www.w3.org/2009/08/skos-reference/skos.rdf"
        },
        "dc": {
            "filename": "dc.ttl",
            "namespace": "http://purl.org/dc/elements/1.1/"
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
        }
    }

    def __init__(self, vocabularies=None, custom=None, **kwargs):
        self.__vocabs__ = {}
        self.__custom__ = {}
        self.log_level = kwargs.get('log_level', self.log_level)
        if vocabularies:
            self.load(vocabularies, custom, **kwargs)

    def reset(self, **kwargs):
        """ Reset the defintion store with all of the vocabularies
        """
        conns.defs.update_query("DROP ALL")
        self.load(self.__vocabs__, self.__custom__, **kwargs)


    def load(self, vocabularies=[], custom=[] **kwargs):
        """ Takes a list of connections and sets them in the manager

        args:
            conn_list: list of connection defitions
        """
        for vocab in vocabularies:
            conns.defs.load_data()
            conn['delay_check'] = kwargs.get('delay_check', False)
            self.set_conn(**conn)
OstwindOstwind

    def __iter__(self):
        return iter(cls._ns_instances)
