""" rdflib API for use with RDF framework """

#! NOT WORKING AT THIS TIME

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
from rdflib import Namespace, Graph, URIRef, ConjunctiveGraph
from .connmanager import RdfwConnections

try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

__author__ = "Mike Stabile, Jeremy Nelson"

CFG = RdfConfigManager()
NSM = RdfNsManager()

class RdflibTstoreSingleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(RdflibTstoreSingleton,
                    cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class RdflibTriplestore(metaclass=RdflibTstoreSingleton):
    """ psuedo triplestore functionality for managing graphs and namespaces
        similar to a triplestore like blazegraph"""
    namespaces = {'kb': ConjunctiveGraph()}

    def has_namespace(self, name):
        """ sees if the namespace exists

        args:
            name(str): the name of the namespace

        returns:
            bool
        """
        if name in self.namespaces:
            return True
        else:
            return False

    def create_namespace(self, name, ignore_errors=False):
        """creates a namespace if it does not exist

        args:
            name: the name of the namespace
            ignore_errors(bool): Will ignore if a namespace already exists or
                    there is an error creating the namespace

        returns:
            True if created
            False if not created
            error if namespace already exists
        """
        if not self.has_namespace(name):
            self.namespaces[name] = ConjunctiveGraph()
            return True
        elif ignore_errors:
            return True
        else:
            raise RuntimeError("namespace '%s' already exists" % name)

    def delete_namespace(self, name, ignore_errors=False):
        """ deletes a namespace

        args:
            name: the name of the namespace
            ignore_errors(bool): Will ignore if a namespace doesn not exist or
                    there is an error deleting the namespace

        returns:
            True if deleted
            False if not deleted
            error if namespace already exists
        """
        if self.has_namespace(name):
            del self.namespaces[name]
            return True
        elif ignore_errors:
            return True
        else:
            raise RuntimeError("namespace '%s' does not exist" % name)

    def get_namespace(self, namespace):
        """ returns the rdflib graph for the specified namespace

        args:
            namespace: the name of the namespace
        """

        if namespace == 'temp':
            return Graph()
        else:
            return self.namespaces[namespace]

class RdflibConn(RdfwConnections):
    """ An API for interacting between rdflib python package and the
        rdfframework

        args:
            url: Not Required or relevant for rdflib
            namespace: The namespace to use
            local_directory: the path to the file data directory as python
                    reads the file path.
            container_dir: Not Required or relevant for rdflib
        """
    vendor = 'rdflib'
    conn_type = 'triplestore'

    # file externsions that contain rdf data
    rdf_formats = ['xml', 'rdf', 'ttl', 'gz', 'nt']
    default_ns = 'kb'
    default_graph = None
    qry_results_formats = ['json',
                           'xml',
                           'application/sparql-results+json',
                           'application/sparql-results+xml']
    check_status = True
    tstore = RdflibTriplestore()

    def __init__(self,
                 url=None,
                 namespace=None,
                 namespace_params=None,
                 local_directory=None,
                 container_dir=None,
                 graph=None,
                 **kwargs):

        self.active = kwargs.get('active', True)
        self.local_directory = pick(local_directory, CFG.LOCAL_DATA_PATH, "")
        self.url = "No Url for Rdflib tstore"
        self.namespace = pick(namespace, self.default_ns)
        self.namespace_params = namespace_params
        self.container_dir = container_dir
        self.graph = pick(graph, self.default_graph)
        try:
            self.conn = self.tstore.get_namespace(self.namespace)
        except KeyError:
            self.tstore.create_namespace(self.namespace)
            self.conn = self.tstore.get_namespace(self.namespace)
        self.__set_mgr__(**kwargs)

    def query(self,
              sparql,
              mode="get",
              namespace=None,
              rtn_format="json",
              **kwargs):
        """ runs a sparql query and returns the results

            args:
                sparql: the sparql query to run
                namespace: the namespace to run the sparql query against
                mode: ['get'(default), 'update'] the type of sparql query
                rtn_format: ['json'(default), 'xml'] format of query results
        """
        if kwargs.get("debug"):
            log.setLevel(logging.DEBUG)
        conn = self.conn
        if namespace and namespace != self.namespace:
            conn = self.tstore.get_namespace(namespace)
        else:
            namespace = self.namespace
        if rtn_format not in self.qry_results_formats:
            raise KeyError("rtn_format was '%s'. Allowed values are %s" % \
                           (rtn_format, self.qry_results_formats))
        if not sparql.strip().lower().startswith("prefix"):
            sparql = "%s\n%s" % (NSM.prefix(), sparql)
        start = datetime.datetime.now()
        if mode == "get":
            try:
                result = json.loads( \
                         conn.query(sparql).serialize(\
                         format=rtn_format).decode()).get('results',
                                                          {}).get('bindings', [])
            except:
                print(sparql)
                raise
        if mode == "update":
            try:
                result = conn.update(sparql)
            except:
                print(sparql)
                raise
        log.debug("\nmode='%s', namespace='%s', rtn_format='%s'\n**** SPAQRL QUERY \n%s\nQuery Time: %s",
                  mode,
                  namespace,
                  rtn_format,
                  sparql,
                  (datetime.datetime.now()-start))
        return result

    def update_query(self, sparql, namespace=None, **kwargs):
        """ runs a sparql update query and returns the results

            args:
                sparql: the sparql query to run
                namespace: the namespace to run the sparql query against
        """
        return self.query(sparql, "update", namespace, **kwargs)

    def load_data(self,
                  data,
                  datatype="ttl",
                  namespace=None,
                  graph=None,
                  is_file=False,
                  **kwargs):
        """ loads data via file stream from python to triplestore

        Args:
          data: The data or filepath to load
          datatype(['ttl', 'xml', 'rdf']): the type of data to load
          namespace: the namespace to use
          graph: the graph to load the data to.
          is_file(False): If true python will read the data argument as a
              filepath, determine the datatype from the file extension,
              read the file and send it to blazegraph as a datastream
        """
        if kwargs.get('debug'):
            log.setLevel(logging.DEBUG)
        time_start = datetime.datetime.now()
        datatype_map = {
            'ttl': 'turtle',
            'xml': 'xml',
            'rdf': 'xml',
            'nt': 'nt',
            'n3': 'n3',
            'nquads': 'nquads',
            'hturtle': 'hturtle'
        }
        if is_file:
            datatype = data.split(os.path.extsep)[-1]
            file_name = data
            log.debug('starting data load of %s', file_name)
            data = open(data, 'rb').read()
        try:
            content_type = datatype_map[datatype]
        except KeyError:
            raise NotImplementedError("'%s' is not an implemented data fromat",
                                      datatype)
        conn = self.conn
        if namespace:
            conn = self.tstore.get_namespace(namespace)
        else:
            namespace = self.namespace
        graph = pick(graph, self.graph)
        start = datetime.datetime.now()
        try:
            result = conn.parse(data=data, publicID=graph, format=content_type)
        except:
            if is_file:
                print("Datafile ", file_name)
            raise
        if is_file:
            log.info (" loaded %s into rdflib namespace '%s'",
                      file_name,
                      namespace)
        else:
            log.info(" loaded data into rdflib namespace '%s' in time: %s",
                     namespace,
                     (datetime.datetime.now() - start))
            return result

    def load_directory(self, method='data_stream', **kwargs):
        """ Uploads data to the Blazegraph Triplestore that is stored in files
            that are in a local directory

            kwargs:
                method['local', 'data_stream']: 'local' uses the container dir
                        'data_stream': reads the file and sends it as part of
                        http request
                file_directory: a string path to the file directory to start
                        the search
                container_dir: the path that the triplestore container sees
                root_dir: root directory to be removed from the file paths
                        for example:
                              file_directory: this is as seen from python app
                                  /example/python/data/dir/to/search
                              container_dir: this is the path as seen from the
                                  triplestore
                                  /data
                              root_dir: the portion of the path to remove so
                                  both directories match
                                  /example/python/data
                file_extensions: a list of file extensions to filter
                        example ['xml', 'rdf']. If none include all files
                include_subfolders: as implied
                namespace: the Blazegraph namespace to load the data
                graph: uri of the graph to load the data. Default is None
                create_namespace: False(default) or True will create the
                        namespace if it does not exist
                use_threading(bool): Whether to use threading or not
        """

        if kwargs.get('reset') == True:
            self.reset_namespace()
        namespace = kwargs.get('namespace', self.namespace)
        container_dir = kwargs.get('container_dir', self.container_dir)
        graph = kwargs.get('graph')
        time_start = datetime.datetime.now()
        include_root = kwargs.get('include_root', False)
        if method == 'data_stream':
            include_root = True
        file_directory = kwargs.get('file_directory', self.local_directory)
        file_extensions = kwargs.get('file_extensions', self.rdf_formats)
        file_list = list_files(file_directory,
                               file_extensions,
                               kwargs.get('include_subfolders', True),
                               include_root=include_root,
                               root_dir=kwargs.get('root_dir',
                                                   self.local_directory))
        log.info(" starting load of '%s' files into namespace '%s'",
                 len(file_list),
                 self.namespace)
        if kwargs.get('create_namespace') and namespace:
            if not self.has_namespace(namespace):
                self.create_namespace(namespace)
        if not self.has_namespace(namespace):
            msg = "".join(["Namespace '%s' does not exist. " % namespace,
                           "Pass kwarg 'create_namespace=True' to ",
                           "auto-create the namespace."])
            raise ValueError(msg)
        params = {}
        for file in file_list:
            if kwargs.get('use_threading') == True:
                if method == 'data_stream':
                    th = threading.Thread(name=file[1],
                                          target=self.load_data,
                                          args=(file[1],
                                                None,
                                                namespace,
                                                graph,
                                                True,))
                else:
                    th = threading.Thread(name=file[1],
                                          target=self.load_local_file,
                                          args=(file[1],
                                                namespace,
                                                graph,))
                th.start()
            else:
              if method == 'data_stream':
                  self.load_data(data=file[1],
                                 namespace=namespace,
                                 graph=graph,
                                 is_file=True)
              else:
                  self.load_local_file(file[1], namespace, graph)
        if kwargs.get('use_threading') == True:
            main_thread = threading.main_thread()
            for t in threading.enumerate():
                if t is main_thread:
                    continue
                t.join()
        log.info("%s file(s) loaded in: %s",
                 len(file_list),
                 datetime.datetime.now() - time_start)

    def load_local_file(self, file_path, namespace=None, graph=None, **kwargs):
        """ Uploads data to the Blazegraph Triplestore that is stored in files
            in  a local directory

            args:
                file_path: full path to the file
                namespace: the Blazegraph namespace to load the data
                graph: uri of the graph to load the data. Default is None
        """
        return self.load_data(file_path,
                              namespace=namespace,
                              graph=graph,
                              is_file=True,
                              **kwargs)

    def has_namespace(self, namespace):
        """ tests to see if the namespace exists

        args:
            namespace: the name of the namespace
        """

        return self.tstore.has_namespace(namespace)

    def create_namespace(self, namespace=None, params=None):
        """ Creates a namespace in the triplestore

        args:
            namespace: the name of the namspace to create
            params: ignore in rdflib connection

        """
        return self.tstore.create_namespace(namespace)

    def delete_namespace(self, namespace):
        """ Deletes a namespace fromt the triplestore

        args:
            namespace: the name of the namespace
        """

        # if not self.has_namespace(namespace):
        #     return "Namespace does not exists"

        return self.tstore.delete_namespace(namespace)


    def __repr__(self):
        return "<rdflib([{'id': '%s', 'namespace': '%s'}])>" % \
               (self.conn.__repr__(), self.namespace)

    def reset_namespace(self, namespace=None, params=None):
        """ Will delete and recreate specified namespace

        args:
            namespace(str): Namespace to reset
            params(dict): params used to reset the namespace
        """
        namespace = pick(namespace, self.namespace)
        params = pick(params, self.namespace_params)
        log.warning(" Reseting namespace '%s' at host: %s",
                 namespace,
                 self.url)
        try:
            self.delete_namespace(namespace)
        except KeyError:
            pass
        self.create_namespace(namespace, params)

    def bulk_load(self, **kwargs):
        """ Uploads data to the Blazegraph Triplestore that is stored in files
            that are in a local directory

            kwargs:
                file_directory: a string path to the file directory
                file_extensions: a list of file extensions to filter
                        example ['xml', 'rdf']. If none include all files
                include_subfolders: as implied
                namespace: the Blazegraph namespace to load the data
                graph: uri of the graph to load the data. Default is None
                create_namespace: False(default) or True will create the
                        namespace if it does not exist
        """
        namespace = kwargs.get('namespace', self.namespace)
        graph = kwargs.get('graph', self.graph)
        if kwargs.get('reset') == True:
            self.reset_namespace()
        file_directory = kwargs.get('file_directory', self.local_directory)
        file_extensions = kwargs.get('file_extensions', self.rdf_formats)
        root_dir = kwargs.get('root_dir', self.local_directory)
        file_list = list_files(file_directory,
                               file_extensions,
                               kwargs.get('include_subfolders', True),
                               include_root=kwargs.get('include_root', False),
                               root_dir=root_dir)
        path_parts = [' ']
        if self.container_dir:
            path_parts.append(self.container_dir)
        file_or_dirs = ",".join([os.path.join(os.path.join(*path_parts),file[1])
                                 for file in file_list]).strip()
        file_or_dirs = "/alliance_data"
        _params = BULK_LOADER_PARAMS.copy()
        params = {
                    'namespace': kwargs.get('namespace', self.namespace),
                    'file_or_dirs': file_or_dirs,
                 }

        _params.update(params)
        time_start = datetime.datetime.now()

        log.info(" starting load of '%s' files into namespace '%s'",
                 len(file_list),
                 params['namespace'])
        new_params = {key: json.dumps(value) \
                      for key, value in _params.items() \
                      if not isinstance(value, str)}
        new_params.update({key: value \
                           for key, value in _params.items() \
                           if isinstance(value, str)})
        data = BULK_LOADER_XML.format(**new_params)
        # data = BULK_LOADER_XML2
        print(data)
        pdb.set_trace()
        url = os.path.join(self.url, 'dataloader')
        result = requests.post(url=url,
                               headers={"Content-Type": 'application/xml'},
                               data=data)
        failed_list = list_files(file_directory,
                                 ['fail'],
                                 kwargs.get('include_subfolders', True),
                                 include_root=kwargs.get('include_root', False),
                                 root_dir=root_dir)
        failed_list = [file for file in failed_list \
                       if file[0].split(".")[-2] in file_extensions]
        good_list = list_files(file_directory,
                               ['good'],
                               kwargs.get('include_subfolders', True),
                               include_root=kwargs.get('include_root', False),
                               root_dir=root_dir)
        # pdb.set_trace()
        log.info(" bulk_load results: %s\nThe following files successfully loaded: \n\t%s",
                 result.text,
                 "\n\t".join([os.path.splitext(file[1])[0] \
                              for file in good_list]))
        if failed_list:
            log.warning("The following files failed to load:\n\t%s",
                     "\n\t".join([file[1] for file in failed_list]))
            log.info(" Attempting load via alt method ***")
            for file in failed_list:
                os.rename(os.path.join(root_dir, file[1]),
                          os.path.join(root_dir, os.path.splitext(file[1])[0]))
                self.load_local_file(os.path.splitext(file[1])[0],
                                     namespace,
                                     graph)
        # restore file names
        files = list_files(file_directory,
                           ['good','fail'],
                           kwargs.get('include_subfolders', True),
                           include_root=kwargs.get('include_root', False),
                           root_dir=root_dir)
        [os.rename(os.path.join(root_dir, file[1]),
                   os.path.join(root_dir, os.path.splitext(file[1])[0])) \
         for file in files]

