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


__author__ = "Mike Stabile, Jeremy Nelson"

MNAME = pyfile_path(inspect.stack()[0][1])
CFG = RdfConfigManager()
NSM = RdfNsManager()

class FedoraCommons(RdfwConnections):
    """ An API for interacting between a Fedora 4 Commans digital repository
        and the rdfframework

        args:
            url: The url to the repository
            local_directory: the path to the file data directory as python
                    reads the file path.
            container_dir: the path to the file data directory as the docker
                    container/Blazegraph see the file path.

        kwargs:
            local_url: alternate url to use if primary is not working
        """
    vendor = "fedora"
    conn_type = "repository"
    log_name = "%s-FedoraCommons" % MNAME
    log_level = logging.INFO
    default_url = ''
    qry_results_formats = {'rdf': 'application/sparql-results+xml',
                           'xml': 'application/sparql-results+xml',
                           'json': 'application/sparql-results+json',
                           'binary': 'application/x-binary-rdf-results-table',
                           'tsv': 'text/tab-separated-values',
                           'cxv': 'text/csv'}

    def __init__(self,
                 url=None,
                 local_directory=None,
                 container_dir=None,
                 **kwargs):

        self.local_directory = pick(local_directory, CFG.LOCAL_DATA_PATH)
        self.ext_url = pick(url, self.default_url)
        self.local_url = pick(kwargs.get('local_url'), self.default_url)
        self.container_dir = container_dir
        self.url = None
        self.active = kwargs.get('active', True)

        if self.ext_url is None:
            msg = ["A Blazegraph url must be defined. Either pass 'url'",
                   "or initialize the 'RdfConfigManager'"]
            raise AttributeError(" ".join(msg))
        if not kwargs.get('delay_check'):
            self.check_status

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
            return True
        except requests.exceptions.ConnectionError:
            pass
        try:
            result = requests.get(self.local_url)
            log.warning("Url '%s' not connecting. Using local_url '%s'" % \
                     (self.ext_url, self.local_url))
            self.url = self.local_url
            return True
        except requests.exceptions.ConnectionError:
            self.url = None
            log.warning("Unable to connect using urls: %s" % set([self.ext_url,
                                                               self.local_url]))
            return False
