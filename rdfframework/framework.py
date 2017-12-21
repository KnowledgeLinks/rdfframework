"""Base Module for RDFFRamework Project"""

__author__ = "Mike Stabile, Jeremy Nelson"


import os
import sys
import inspect
import logging
import time
import operator
import requests
import pdb
import rdflib
import shutil

from flask import json
from rdfframework.utilities import render_without_request, list_files, DictClass
from rdfframework.configuration import RdfConfigManager
from rdfframework.rdfclass import RdfPropertyFactory, RdfClassFactory
from rdfframework.datasets import RdfDataset
from rdfframework.sparql import get_graph
from rdfframework.datatypes import RdfNsManager

MODULE_NAME = os.path.basename(inspect.stack()[0][1])
CFG = RdfConfigManager()
NSM = RdfNsManager()

class RdfFrameworkSingleton(type):
    """Singleton class for the RdfFramewodk that will allow for only one
    instance of the RdfFramework to be created."""

    _instances = {}
    def __call__(cls, *args, **kwargs):
        if not CFG.is_initialized:
            # print("The RdfConfigManager has not been initialized!")
            pass
        if cls not in cls._instances:
            cls._instances[cls] = super(RdfFrameworkSingleton,
                    cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class RdfFramework(metaclass=RdfFrameworkSingleton):
    ''' base class for initializing Knowledge Links' Graph database RDF
        vocabulary framework'''

    log_name = "%s.RdfFramework" % MODULE_NAME
    # set specific logging handler for the module allows turning on and off
    # debug as required
    log_level = logging.DEBUG

    def __init__(self, **kwargs):

        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
        log.setLevel(self.log_level)

        config = kwargs.get('config')
        if config:
            print("Should find value")
            CFG = RdfConfigManager(config=config)
        else:
            raise EnvironmentError("kwarg 'config' is required")
        self.cfg = CFG
        NSM = RdfNsManager(config=CFG)
        self.root_file_path = CFG.RDF_DEFINITION_FILE_PATH
        self._set_datafiles()
        self.rml = DictClass()
        # if the the definition files have been modified since the last json
        # files were saved reload the definition files
        reset = kwargs.get('reset',False)
        # verify that the server core is up and running
        servers_up = True
        if kwargs.get('server_check', True):
            servers_up = verify_server_core(600, 0)
        else:
            log.info("server check skipped")
        if not servers_up:
            log.info("Sever core not initialized --- Framework Not loaded")
        if servers_up:
            log.info("*** Loading Framework ***")
            self._load_data(reset)
            RdfPropertyFactory(CFG.def_tstore, reset=reset)
            RdfClassFactory(CFG.def_tstore, reset=reset)
            log.info("*** Framework Loaded ***")

    def load_rml(self, rml_name):
        """ loads an rml mapping into memory

        args:
            rml_name(str): the name of the rml file
        """
        conn = CFG.rml_tstore
        cache_path = os.path.join(CFG.CACHE_DATA_PATH, 'rml_files', rml_name)
        if not os.path.exists(cache_path):
            results = get_graph(NSM.uri(getattr(NSM.kdr, rml_name), False),
                                conn)
            with open(cache_path, "w") as file_obj:
                file_obj.write(json.dumps(results, indent=4))
        else:
            results = json.loads(open(cache_path).read())
        self.rml[rml_name] = RdfDataset(results)
        return self.rml[rml_name]

    def get_rml(self, rml_name):
        """ returns the rml mapping RdfDataset

        rml_name(str): Name of the rml mapping to retrieve
        """

        try:
            return getattr(self, rml_name)
        except AttributeError:
            return self.load_rml(rml_name)



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

    def _load_data(self, reset=False):
        ''' loads the RDF/turtle application data to the triplestore

        args:
            reset(bool): True will delete the definition dataset and reload
                    all of the datafiles.
        '''

        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
        log.setLevel(self.log_level)
        for attr, obj in self.datafile_obj.items():
            if reset or obj['latest_mod'] > obj['last_json_mod']:
                conn = obj['conn']
                sparql = "DROP ALL;"
                if os.path.isdir(obj['cache_path']):
                    shutil.rmtree(obj['cache_path'], ignore_errors=True)
                os.makedirs(obj['cache_path'])
                drop_extensions = conn.update_query(sparql)
                rdf_resource_templates = []
                rdf_data = []
                for path, files in obj['files'].items():
                    for file in files:
                        file_path = os.path.join(path, file)
                        # data = open(file_path).read()
                        # log.info(" uploading file: %s | namespace: %s",
                        #          file,
                        #          conn.namespace)
                        # data_type = file.split('.')[-1]
                        result = conn.load_data(file_path,
                                                #datatype=data_type,
                                                graph=str(getattr(NSM.kdr,
                                                                  file)),
                                                is_file=True)
                        if result.status_code > 399:
                            raise ValueError("Cannot load '{}' into {}".format(
                                file_name, conn))

    def _set_data_filelist(self,
                           start_path,
                           attr_name,
                           conn,
                           file_exts=[],
                           dir_filter=set()):
        ''' does a directory search for data files '''

        def filter_path(filter_terms, dir_path):
            """ sees if any of the terms are present in the path if so returns
                True

            args:
                filter_terms(list): terms to check
                dir_path: the path of the directory
            """
            if filter_terms.intersection(set(dir_path.split(os.path.sep))):
                return True
            else:
                return False

        data_obj = {}
        files_dict = {}
        latest_mod = 0
        dir_filter = set(dir_filter)
        for root, dirnames, filenames in os.walk(start_path):
            if not dir_filter or filter_path(dir_filter, root):
                if file_exts:
                    filenames = [x for x in filenames
                                 if x.split('.')[-1].lower() in file_exts]
                files_dict[root] = filenames
                for def_file in filenames:
                    file_mod = os.path.getmtime(os.path.join(root,def_file))
                    if file_mod > latest_mod:
                        latest_mod = file_mod
        data_obj['latest_mod'] = latest_mod
        data_obj['files'] = files_dict
        json_mod = 0
        cache_path = os.path.join(CFG.CACHE_DATA_PATH, attr_name)
        if cache_path:
            for root, dirnames, filenames in os.walk(cache_path):
                for json_file in filenames:
                    file_mod = os.path.getmtime(os.path.join(root,json_file))
                    if file_mod > json_mod:
                        json_mod = file_mod
        data_obj['last_json_mod'] = json_mod
        data_obj['conn'] = conn
        data_obj['cache_path'] = cache_path
        self.datafile_obj[attr_name] = data_obj

def verify_server_core(timeout=120, start_delay=90):
    ''' checks to see if the server_core is running

        args:
            delay: will cycle till core is up.
            timeout: number of seconds to wait
    '''
    timestamp = time.time()
    last_check = time.time() + start_delay - 10
    last_delay_notification = time.time() - 10
    server_down = True
    return_val = False
    timeout += 1
    # loop until the server is up or the timeout is reached
    while((time.time()-timestamp) < timeout) and server_down:
        # if delaying, the start of the check, print waiting to start
        if start_delay > 0 and time.time() - timestamp < start_delay \
                and (time.time()-last_delay_notification) > 5:
            print("Delaying server status check until %ss. Current time: %ss" \
                    % (start_delay, int(time.time() - timestamp)))
            last_delay_notification = time.time()
        # send a request check every 10s until the server is up
        while ((time.time()-last_check) > 10) and server_down:
            print("Checking status of servers at %ss" % \
                    int((time.time()-timestamp)))
            last_check = time.time()
            try:
                repo = requests.get(CFG.REPOSITORY_URL)
                repo_code = repo.status_code
                print ("\t", CFG.REPOSITORY_URL, " - ", repo_code)
            except:
                repo_code = 400
                print ("\t", CFG.REPOSITORY_URL, " - DOWN")
            try:
                triple = requests.get(CFG.DATA_TRIPLESTORE.url)
                triple_code = triple.status_code
                print ("\t", CFG.DATA_TRIPLESTORE.url, " - ", triple_code)
            except:
                triple_code = 400
                print ("\t", CFG.DATA_TRIPLESTORE.url, " - down")
            if repo_code == 200 and triple_code == 200:
                server_down = False
                return_val = True
                print("**** Servers up at %ss" % \
                    int((time.time()-timestamp)))
                break
    return return_val
