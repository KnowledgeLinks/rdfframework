""" Blazegraph API for use with RDF framework """
import os
import datetime
import inspect
import logging
import json
import requests
import threading
import pdb

from bs4 import BeautifulSoup
from rdfframework.utilities import (list_files,
                                    pick,
                                    pyfile_path,
                                    format_multiline)
from rdfframework.configuration import RdfConfigManager
from rdfframework.datatypes import RdfNsManager
from rdfframework.sparql import add_sparql_line_nums
from .connmanager import RdfwConnections
try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

__author__ = "Mike Stabile, Jeremy Nelson"

CFG = RdfConfigManager()
NSM = RdfNsManager()

class Blazegraph(RdfwConnections):
    """
    An API for interacting between a Blazegraph triplestore and the
    rdfframework

    args:
        url: The url to the triplestore
        namespace: The namespace to use. Different namespaces function as
              different triplestores
        local_directory: the path to the file data directory as python
                reads the file path.
        container_dir: the path to the file data directory as the docker
                container/Blazegraph see the file path.

    kwargs:
         namespace_params: Dictionary of Blazegraph paramaters.
                defaults are:
                    {'axioms': 'com.bigdata.rdf.axioms.NoAxioms',
                     'geoSpatial': False,
                     'isolatableIndices': False,
                     'justify': False,
                     'quads': False,
                     'rdr': False,
                     'textIndex': False,
                     'truthMaintenance': False}
         graph: the RDF graph URI for the connection. Defaults to all graphs
         debug: sets the logging level to DEBUG
         log_level: sets the logging level for the module
         delay_check[bool]: do not check server status on initilization
    """
    vendor = "blazegraph"
    conn_type = "triplestore"
    # maps the blazegraph paramater to the userfriendly short name
    ns_property_map = {
        "axioms": "com.bigdata.rdf.store.AbstractTripleStore.axiomsClass",
        "geoSpatial": "com.bigdata.rdf.store.AbstractTripleStore.geoSpatial",
        "isolatableIndices": "com.bigdata.rdf.sail.isolatableIndices",
        "justify": "com.bigdata.rdf.store.AbstractTripleStore.justify",
        "namespace": "com.bigdata.rdf.sail.namespace",
        "quads": "com.bigdata.rdf.store.AbstractTripleStore.quads",
        "rdr": "com.bigdata.rdf.store.AbstractTripleStore.statementIdentifiers",
        "textIndex": "com.bigdata.rdf.store.AbstractTripleStore.textIndex",
        "truthMaintenance": "com.bigdata.rdf.sail.truthMaintenance"
    }
    default_ns = 'kb'
    default_graph = "bd:nullGraph"
    default_url = 'http://localhost:9999/blazegraph/sparql'
    qry_results_formats = {'rdf': 'application/sparql-results+xml',
                           'xml': 'application/sparql-results+xml',
                           'json': 'application/sparql-results+json',
                           'binary': 'application/x-binary-rdf-results-table',
                           'tsv': 'text/tab-separated-values',
                           'csv': 'text/csv'}
    # file extensions that contain rdf data
    rdf_formats = {'rdf': 'application/rdf+xml',
                   'xml': 'application/rdf+xml',
                   'json-ld': 'application/ld+json',
                   'nt': 'text/plain',
                   'gz': 'text/plain',
                   'ntx': 'application/x-n-triples-RDR',
                   'ttl': 'application/x-turtle',
                   'turtle': 'application/x-turtle',
                   'ttlx': 'application/x-turtle-RDR',
                   'n3': 'text/rdf+n3',
                   'trix': 'application/trix',
                   'trig': 'application/x-trig',
                   'nq': 'text/x-nquads',
                   'json': 'application/sparql-results+json'}

    qry_formats = rdf_formats.copy()
    qry_formats.update(qry_results_formats)

    def __init__(self,
                 url=None,
                 namespace=None,
                 namespace_params=None,
                 local_directory=None,
                 container_dir=None,
                 graph=None,
                 **kwargs):

        self.local_directory = pick(local_directory, CFG.dirs.data)
        self.ext_url = pick(url, self.default_url)
        self.local_url = pick(kwargs.get('local_url'), self.default_url)
        self.log_level = log.level
        log.setLevel(kwargs.get("log_level", log.level))
        self.namespace = pick(namespace, self.default_ns)
        self.namespace_params = namespace_params
        self.container_dir = container_dir
        self.graph = pick(graph, self.default_graph)
        self.url = None
        self.active = kwargs.get('active', True)

        if self.ext_url is None:
            msg = ["A Blazegraph url must be defined. Either pass 'url'",
                   "or initialize the 'RdfConfigManager'"]
            raise AttributeError(" ".join(msg))
        if not kwargs.get('delay_check'):
            self.check_status
        self.__set_mgr__(**kwargs)

    @property
    def check_status(self):
        """ tests both the ext_url and local_url to see if the database is
            running

            returns:
                True if a connection can be made
                False if the connection cannot me made
        """

        def validate_namespace(self):
            if not self.has_namespace(self.namespace):
                log.warning(format_multiline(["",
                                              """\tnamespace '{}' does not
                                              exist. Creating namespace"""],
                                              self.namespace))
                self.create_namespace(self.namespace)

        if self.url:
            return True
        try:
            result = requests.get(self._make_url(self.namespace,
                                                 self.ext_url,
                                                 check_status_call=True))
            self.url = self.ext_url
            validate_namespace(self)
            return True
        except requests.exceptions.ConnectionError:
            pass
        try:
            result = requests.get(self._make_url(self.namespace,
                                                 self.local_url,
                                                 check_status_call=True))
            log.warning("Url '%s' not connecting. Using local_url '%s'" % \
                     (self.ext_url, self.local_url))
            self.url = self.local_url
            validate_namespace(self)
            return True
        except requests.exceptions.ConnectionError:
            self.url = None
            log.warning("Unable to connect using urls: %s" % set([self.ext_url,
                                                               self.local_url]))
            return False

    def query(self,
              sparql,
              mode="get",
              namespace=None,
              rtn_format="json",
              **kwargs):
        """
        Runs a sparql query and returns the results

        Args:
        -----
            sparql: the sparql query to run
            namespace: the namespace to run the sparql query against
            mode: ['get'(default), 'update'] the type of sparql query
            rtn_format: ['json'(default), 'xml'] format of query results

        Kwargs:
        -------
            debug(bool): If True sets logging level to debug
        """
        namespace = pick(namespace, self.namespace)
        if kwargs.get("log_level"):
            log.setLevel(kwargs['log_level'])
        if kwargs.get("debug"):
            log.setLevel(logging.DEBUG)
        if rtn_format not in self.qry_formats:
            raise KeyError("rtn_format was '%s'. Allowed values are %s" % \
                           (rtn_format, self.qry_results_formats))
        url = self._make_url(namespace)
        if 'prefix' not in sparql.lower():
            sparql = "%s\n%s" % (NSM.prefix(), sparql)


        if mode == "get":

            data = {"query": sparql} #, "format": rtn_format}
        elif mode == "update":
            data = {"update": sparql}
        else:
            raise NotImplementedError("'mode' != to ['get', 'update']")

        headers = {'Accept': self.qry_formats[rtn_format]}
        start = datetime.datetime.now()
        try:
            result = requests.post(url, data=data, headers=headers)
        except requests.exceptions.ConnectionError:
            result = requests.post(self._make_url(namespace, self.local_url),
                                   data=data,
                                   headers=headers)
        log.debug(format_multiline(["",
                                    "url='{url}'",
                                    """mode='{mode}', namespace='{namespace}',
                                    rtn_format='{rtn_format}'""",
                                    "**** SPAQRL QUERY ****",
                                    "",
                                    "{sparql}",
                                    "Query Time: {q_time}"],
                                   url=url,
                                   mode=mode,
                                   namespace=namespace,
                                   rtn_format=rtn_format,
                                   sparql=sparql,
                                   q_time=(datetime.datetime.now()-start),
                                   **kwargs))

        if result.status_code == 200:
            try:
                if rtn_format == "json":
                    bindings = result.json().get('results',
                                                 {}).get('bindings', [])
                elif rtn_format == 'xml':
                    xml_doc = etree.XML(result.text)
                    bindings = xml_doc.findall("results/bindings")
                else:
                    bindings = result.text
                try:
                    log.debug("result count: %s", len(bindings))
                except TypeError:
                    pass
                return bindings
            except json.decoder.JSONDecodeError:
                if mode == 'update':
                    return BeautifulSoup(result.text, 'lxml').get_text()
                return result.text
        else:
            raise SyntaxError("%s\n\n%s\n\n%s" % (sparql,
                    add_sparql_line_nums(sparql),
                    result.text[result.text.find("java."):]))

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
        """
        Loads data via file stream from python to triplestore

        Args:
        -----
          data: The data or filepath to load
          datatype(['ttl', 'xml', 'rdf']): the type of data to load
          namespace: the namespace to use
          graph: the graph to load the data to.
          is_file(False): If true python will read the data argument as a
              filepath, determine the datatype from the file extension,
              read the file and send it to blazegraph as a datastream
        """
        log.setLevel(kwargs.get("log_level", self.log_level))
        time_start = datetime.datetime.now()
        datatype_map = {
            'ttl': 'text/turtle',
            'xml': 'application/rdf+xml',
            'rdf': 'application/rdf+xml',
            'nt': 'text/plain'
        }
        if is_file:
            datatype = data.split(os.path.extsep)[-1]
            file_name = data
            log.debug('starting data load of %s', file_name)
            data = open(data, 'rb').read()
        else:
            try:
                data = data.encode('utf-8')
            except AttributeError:
                # data already encoded
                pass
        try:
            content_type = datatype_map[datatype]
        except KeyError:
            raise NotImplementedError("'%s' is not an implemented data format",
                                      datatype)
        context_uri = pick(graph, self.graph)
        result = requests.post(url=self._make_url(namespace),
                               headers={"Content-Type": content_type},
                               params={"context-uri": context_uri},
                               data=data)
        if result.status_code == 200:
            if is_file:
                log.info (" loaded %s into blazegraph - %s",
                          file_name,
                          self.format_response(result.text))
            else:
                log.info(" loaded data - %s", self.format_response(result.text))
            log.setLevel(self.log_level)
            return result
        else:
            raise SyntaxError(result.text)

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
        root_dir = kwargs.get('root_dir', self.local_directory)
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
                               root_dir=root_dir)
        log.info(" starting load of '%s' files into namespace '%s'",
                 len(file_list),
                 self.namespace)
        url = self._make_url(namespace)
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

    @staticmethod
    def format_response(text):
        try:
            xml_json = dict(etree.XML(text).items())
        except:
            parts = text.split(">")
            xml_json = dict(etree.XML(">".join(parts[:-1] + [''])))
            xml_json[' '] = parts[-1]
        return str(xml_json).replace("{","").replace("}","")

    def load_local_file(self, file_path, namespace=None, graph=None, **kwargs):
        """ Uploads data to the Blazegraph Triplestore that is stored in files
            in directory that is available locally to blazegraph

            args:
                file_path: full path to the file
                namespace: the Blazegraph namespace to load the data
                graph: uri of the graph to load the data. Default is None

            kwargs:
                container_dir: the directory as seen by blazegraph - defaults to
                        instance attribute if not passed
        """
        time_start = datetime.datetime.now()
        url = self._make_url(namespace)
        params = {}
        if graph:
            params['context-uri'] = graph
        new_path = []
        container_dir = pick(kwargs.get('container_dir'), self.container_dir)
        if container_dir:
            new_path.append(self.container_dir)
        new_path.append(file_path)
        params['uri'] = "file:///%s" % os.path.join(*new_path)
        log.debug(" loading %s into blazegraph", file_path)
        result = requests.post(url=url, params=params)
        if result.status_code > 300:
            raise SyntaxError(result.text)
        log.info("loaded '%s' in time: %s blazegraph response: %s",
                 file_path,
                 datetime.datetime.now() - time_start,
                 self.format_response(result.text))
        return result

    def has_namespace(self, namespace):
        """ tests to see if the namespace exists

        args:
            namespace: the name of the namespace
        """
        result = requests.get(self._make_url(namespace))
        if result.status_code == 200:
            return True
        elif result.status_code == 404:
            return False

    def create_namespace(self, namespace=None, params=None):
        """ Creates a namespace in the triplestore

        args:
            namespace: the name of the namspace to create
            params: Dictionary of Blazegraph paramaters. defaults are:

                    {'axioms': 'com.bigdata.rdf.axioms.NoAxioms',
                     'geoSpatial': False,
                     'isolatableIndices': False,
                     'justify': False,
                     'quads': False,
                     'rdr': False,
                     'textIndex': False,
                     'truthMaintenance': False}
        """
        namespace = pick(namespace, self.namespace)
        params = pick(params, self.namespace_params)
        if not namespace:
            raise ReferenceError("No 'namespace' specified")
        _params = {'axioms': 'com.bigdata.rdf.axioms.NoAxioms',
                   'geoSpatial': False,
                   'isolatableIndices': False,
                   'justify': False,
                   'namespace': namespace,
                   'quads': True,
                   'rdr': False,
                   'textIndex': False,
                   'truthMaintenance': False}
        if params:
            _params.update(params)
        content_type = "text/plain"
        url = self._make_url("prepareProperties").replace("/sparql", "")
        params = ["%s=%s" % (map_val,
                             json.dumps(_params[map_key]).replace("\"", "")) \
                  for map_key, map_val in self.ns_property_map.items()]
        params = "\n".join(params)
        result = requests.post(url=url,
                               headers={"Content-Type": content_type},
                               data=params)
        data = result.text
        content_type = "application/xml"
        url = self._make_url("x").replace("/x/sparql", "")
        result = requests.post(url=url,
                               headers={"Content-Type": content_type},
                               data=data)
        if result.status_code == 201:
            log.warning(result.text)
            return result.text
        else:
            raise RuntimeError(result.text)

    def delete_namespace(self, namespace):
        """ Deletes a namespace fromt the triplestore

        args:
            namespace: the name of the namespace
        """

        # if not self.has_namespace(namespace):
        #     return "Namespace does not exists"

        # log = logging.getLogger("%s.%s" % (self.log_name,
        #                                    inspect.stack()[0][3]))
        # log.setLevel(self.log_level)

        url = self._make_url(namespace).replace("/sparql", "")
        result = requests.delete(url=url)
        if result.status_code == 200:
            log.critical(result.text)
            return result.text
        raise RuntimeError(result.text)

    def _make_url(self, namespace=None, url=None, **kwargs):
        """ Creates the REST Url based on the supplied namespace

        args:
            namespace: string of the namespace
        kwargs:
            check_status_call: True/False, whether the function is called from
                    check_status. Used to avoid recurrsion error
        """
        if not kwargs.get("check_status_call"):
            if not self.url:
                self.check_status
        rtn_url = self.url
        if url:
            rtn_url = url
        if rtn_url is None:
            rtn_url = self.ext_url
        namespace = pick(namespace, self.namespace)
        if namespace:
            rtn_url = os.path.join(rtn_url.replace("sparql", ""),
                                   "namespace",
                                   namespace,
                                   "sparql").replace("\\", "/")
        elif not rtn_url.endswith("sparql"):
            rtn_url = os.path.join(rtn_url, "sparql").replace("\\", "/")
        return rtn_url

    def reset_namespace(self, namespace=None, params=None):
        """ Will delete and recreate specified namespace

        args:
            namespace(str): Namespace to reset
            params(dict): params used to reset the namespace
        """
        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
        log.setLevel(self.log_level)
        namespace = pick(namespace, self.namespace)
        params = pick(params, self.namespace_params)
        log.warning(" Reseting namespace '%s' at host: %s",
                 namespace,
                 self.url)
        try:
            self.delete_namespace(namespace)
        except RuntimeError:
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
        log.debug(data)
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

BULK_LOADER_XML = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">
    <properties>
        <!-- RDF Format (Default is rdf/xml) -->
        <entry key="format">{data_format}</entry>
        <!-- Base URI (Optional) -->
        <entry key="baseURI"></entry>
        <!-- Default Graph URI (Optional - Required for quads mode namespace) -->
        <entry key="defaultGraph">{graph}</entry>
        <!-- Suppress all stdout messages (Optional) -->
        <entry key="quiet">{messages}</entry>
        <!-- Show additional messages detailing the load performance. (Optional) -->
        <entry key="verbose">{verbose}</entry>
       <!-- Compute the RDF(S)+ closure. (Optional) -->
             <entry key="closure">{closure}</entry>
       <!-- Files will be renamed to either .good or .fail as they are processed.
                   The files will remain in the same directory. -->
       <entry key="durableQueues">{durable_queues}</entry>
       <!-- The namespace of the KB instance. Defaults to kb. -->
       <entry key="namespace">{namespace}</entry>
       <!-- The configuration file for the database instance. It must be readable by the web application. -->
             <entry key="propertyFile">{property_file}</entry>
       <!-- Zero or more files or directories containing the data to be loaded.
                   This should be a comma delimited list. The files must be readable by the web application. -->
           <entry key="fileOrDirs">{file_or_dirs}</entry>
      </properties>
"""

BULK_LOADER_XML2 = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">
    <properties>
        <!-- RDF Format (Default is rdf/xml) -->
        <entry key="format">rdf/xml</entry>
        <!-- Base URI (Optional) -->
        <entry key="baseURI"></entry>
        <!-- Default Graph URI (Optional - Required for quads mode namespace) -->
        <entry key="defaultGraph"></entry>
        <!-- Suppress all stdout messages (Optional) -->
        <entry key="quiet">false</entry>
        <!-- Show additional messages detailing the load performance. (Optional) -->
        <entry key="verbose">0</entry>
       <!-- Compute the RDF(S)+ closure. (Optional) -->
             <entry key="closure">false</entry>
       <!-- Files will be renamed to either .good or .fail as they are processed.
                   The files will remain in the same directory. -->
       <entry key="durableQueues">true</entry>
       <!-- The namespace of the KB instance. Defaults to kb. -->
       <entry key="namespace">kb</entry>
       <!-- The configuration file for the database instance. It must be readable by the web application. -->
             <entry key="propertyFile">/opt/triplestore/RWStore.properties</entry>
       <!-- Zero or more files or directories containing the data to be loaded.
                   This should be a comma delimited list. The files must be readable by the web application. -->
           <entry key="fileOrDirs"></entry>
      </properties>"""

BULK_LOADER_PARAMS = {
    'data_format':'text/turtle',
    'graph': "bd:nullGraph",
    'messages': True,
    'closure': False,
    'verbose': 1,
    'durable_queues': True,
    'namespace': "kb",
    'file_or_dirs': "adfadf",
    'property_file': "/opt/triplestore/RWStore.properties"
}
