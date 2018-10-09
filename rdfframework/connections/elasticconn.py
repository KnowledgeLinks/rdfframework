import os
import datetime
import inspect
import logging
import json
import requests
import threading
import pdb

from bs4 import BeautifulSoup
from rdfframework.utilities import list_files, pick, pyfile_path
from rdfframework.configuration import RdfConfigManager
from rdfframework.datatypes import RdfNsManager
from .connmanager import RdfwConnections
from rdfframework.search import EsBase
from elasticsearch import Elasticsearch

__author__ = "Mike Stabile, Jeremy Nelson"

MNAME = pyfile_path(inspect.stack()[0][1])
CFG = RdfConfigManager()
NSM = RdfNsManager()

class Elastic(EsBase, RdfwConnections):
    """ An API for interacting between elasticsearch and the rdfframework
    this is a simple extension of the elasticsearch package

        args:
            url: The url to the repository
            local_directory: the path to the file data directory as python
                    reads the file path.
            container_dir: the path to the file data directory as the docker
                    container/Blazegraph see the file path.

        kwargs:
            local_url: alternate url to use if primary is not working
        """
    vendor = "elastic"
    conn_type = "search"
    log_name = "%s-Elastic" % MNAME
    log_level = logging.INFO
    default_url = 'http://localhost:9200'


    def __init__(self,
                 url=None,
                 local_directory=None,
                 container_dir=None,
                 **kwargs):

        self.local_directory = pick(local_directory, CFG.LOCAL_DATA_PATH)
        self.ext_url = pick(url, self.default_url)
        self.local_url = pick(kwargs.get('local_url'), self.default_url)
        self.url = None
        self.active = kwargs.get('active', True)

        if not kwargs.get('delay_check'):
            self.check_status
        if self.url:
            kwargs['es_url'] = self.url
        else:
            kwargs['es_url'] = self.ext_url
        super(Elastic, self).__init__(**kwargs)
        self.container_dir = container_dir


        if self.ext_url is None:
            msg = ["A Elasticsearch url must be defined. Either pass 'url'",
                   "or initialize the 'RdfConfigManager'"]
            raise AttributeError(" ".join(msg))

    def __repr__(self):
        url = self.ext_url
        if self.url:
            url = self.url
        return "<Elastic([{'host': '%s'}])>" % url
    @property
    def check_status(self):
        """ tests both the ext_url and local_url to see if the database is
            running

            returns:
                True if a connection can be made
                False if the connection cannot me made
        """
        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
        log.setLevel(self.log_level)

        if self.url:
            return True
        try:
            result = requests.get(self.ext_url)
            self.url = self.ext_url
            self.es_url = self.url
            self.es = Elasticsearch([self.url])
            return True
        except requests.exceptions.ConnectionError:
            pass
        try:
            result = requests.get(self.local_url)
            log.warning("Url '%s' not connecting. Using local_url '%s'" % \
                     (self.ext_url, self.local_url))
            self.url = self.local_url
            self.es_url = self.url
            self.es = Elasticsearch([self.url])
            return True
        except requests.exceptions.ConnectionError:
            self.url = None
            log.warning("Unable to connect using urls: %s" % set([self.ext_url,
                                                               self.local_url]))
            return False
