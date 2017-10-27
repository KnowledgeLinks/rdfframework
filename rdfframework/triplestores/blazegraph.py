""" Blazegraph API for use with RDF framework """
import os
import datetime
import inspect
import logging
import json
import requests

from bs4 import BeautifulSoup
from rdfframework.utilities import RdfConfigManager, list_files, pick, \
                                   pyfile_path, RdfNsManager

__author__ = "Mike Stabile, Jeremy Nelson"

MNAME = pyfile_path(inspect.stack()[0][1])
CFG = RdfConfigManager()
NSM = RdfNsManager()

class Blazegraph(object):
    """ An API for interacting between a Blazegraph triplestore and the
        rdfframework

        args:
            url: The url to the triplestore
            namespace: The namespace to use
            local_directory: the path to the file data directory as python
                    reads the file path.
            container_dir: the path to the file data directory as the docker
                    container/Blazegraph see the file path.
        """
    log_name = "%s-Blazegraph" % MNAME
    log_level = logging.INFO

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
    # file externsions that contain rdf data
    default_exts = ['xml', 'rdf', 'ttl', 'gz', 'nt']
    default_ns = 'kb'
    default_graph = "bd:nullGraph"
    qry_results_formats = ['json',
                           'xml',
                           'application/sparql-results+json',
                           'application/sparql-results+xml']
    def __init__(self,
                 url=None,
                 namespace=None,
                 local_directory=None,
                 container_dir=None,
                 graph=None):

        self.local_directory = pick(local_directory, CFG.LOCAL_DATA_PATH)
        self.url = pick(url,
                        CFG.DATA_TRIPLESTORE.url,
                        CFG.DEFINITION_TRIPLESTORE.url)
        self.namespace = pick(namespace,
                              CFG.DATA_TRIPLESTORE.namespace,
                              CFG.DEFINITION_TRIPLESTORE.namespace,
                              self.default_ns)
        self.container_dir = pick(container_dir,
                                  CFG.DATA_TRIPLESTORE.container_dir,
                                  CFG.DEFINITION_TRIPLESTORE.container_dir)
        self.graph = pick(graph,
                          CFG.DATA_TRIPLESTORE.graph,
                          CFG.DEFINITION_TRIPLESTORE.graph,
                          self.default_graph)
        if self.url is None:
            msg = ["A Blazegraph url must be defined. Either pass 'url'",
                   "or initialize the 'RdfConfigManager'"]
            raise AttributeError(" ".join(msg))

    def query(self, sparql, mode="get", namespace=None, rtn_format="json"):
        """ runs a sparql query and returns the results

            args:
                sparql: the sparql query to run
                namespace: the namespace to run the sparql query against
                mode: ['get'(default), 'update'] the type of sparql query
                rtn_format: ['json'(default), 'xml'] format of query results
        """
        if rtn_format not in self.qry_results_formats:
            raise KeyError("rtn_format was '%s'. Allowed values are %s" % \
                           (rtn_format, self.qry_results_formats))
        url = self._make_url(namespace)
        if not sparql.lower().startswith("prefix"):
            sparql = "%s\n%s" % (NSM.prefix(), sparql)
        if mode == "get":
            data = {"query": sparql, "format": rtn_format}

        elif mode == "update":
            data = {"update": sparql}
        else:
            raise NotImplementedError("'mode' != to ['get', 'update']")
        result = requests.post(url, data=data)
        if result.status_code == 200:
            try:
                return result.json().get('results', {}).get('bindings', [])
            except json.decoder.JSONDecodeError:
                if mode == 'update':
                    return BeautifulSoup(result.text, 'lxml').get_text()
                return result.text
        else:
            raise SyntaxError(result.text)

    def update_query(self, sparql, namespace=None):
        """ runs a sparql update query and returns the results

            args:
                sparql: the sparql query to run
                namespace: the namespace to run the sparql query against
        """
        return self.query(sparql, "update", namespace)

    def load_data(self,
                  data,
                  datatype="ttl",
                  namespace=None,
                  graph=None):
        """ loads data via file stream from python to triplestore

        Args:
          data: The data to load
          datatype(['ttl', 'xml', 'rdf']): the type of data to load
          namespace: the namespace to use
          graph: the graph to load the data to.
        """
        datatype_map = {
            'ttl': 'text/turtle',
            'xml': 'application/rdf+xml',
            'rdf': 'application/rdf+xml'
        }
        try:
            content_type = datatype_map[datatype]
        except KeyError:
            raise NotImplementedError("'%s' is not an implemented data fromat",
                                      datatype)
        context_uri = pick(graph, self.graph)
        result = requests.post(url=self._make_url(namespace),
                               headers={"Content-Type": content_type},
                               params={"context-uri": context_uri},
                               data=data.encode('utf-8'))
        if result.status_code == 200:
            return result
        else:
            raise SyntaxError(result.text)

    def load_local_directory(self, **kwargs):
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

        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
        log.setLevel(self.log_level)

        namespace = kwargs.get('namespace', self.namespace)
        time_start = datetime.datetime.now()
        file_directory = kwargs.get('file_directory', self.local_directory)
        file_extensions = kwargs.get('file_extensions', self.default_exts)
        file_list = list_files(file_directory,
                               file_extensions,
                               kwargs.get('include_subfolders', True),
                               include_root=kwargs.get('include_root', False),
                               root_dir=kwargs.get('root_dir',
                                                   self.local_directory))
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
        if kwargs.get('graph'):
            params['context-uri'] = kwargs['graph']
        path_parts = []
        if self.container_dir:
            path_parts.append(self.container_dir)

        for file in file_list:
            new_path = path_parts.copy()
            new_path.append(file[1])
            params['uri'] = "file:///%s" % os.path.join(*new_path)
            log.info("loading %s into blazegraph", file[0])
            result = requests.post(url=url, params=params)
            if result.status_code > 300:
                raise SyntaxError(result.text)
        log.info("%s file(s) loaded in: %s",
                 len(file_list),
                 datetime.datetime.now() - time_start)

    def load_local_file(self, file_path, namespace=None, graph=None):
        """ Uploads data to the Blazegraph Triplestore that is stored in files
            in  a local directory

            args:
                file_path: full path to the file
                namespace: the Blazegraph namespace to load the data
                graph: uri of the graph to load the data. Default is None
        """
        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
        log.setLevel(self.log_level)
        time_start = datetime.datetime.now()
        url = self._make_url(namespace)
        params = {}
        if graph:
            params['context-uri'] = graph
        new_path = []
        if self.container_dir:
            new_path.append(self.container_dir)
        new_path.append(file_path)
        params['uri'] = "file:///%s" % os.path.join(*new_path)
        log.info("loading %s into blazegraph", file_path)
        result = requests.post(url=url, params=params)
        if result.status_code > 300:
            raise SyntaxError(result.text)
        log.info("%s file(s) loaded in: %s",
                 1,
                 datetime.datetime.now() - time_start)
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

    def create_namespace(self,
                         namespace,
                         params=None):
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
        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
        log.setLevel(self.log_level)

        _params = {'axioms': 'com.bigdata.rdf.axioms.NoAxioms',
                   'geoSpatial': False,
                   'isolatableIndices': False,
                   'justify': False,
                   'namespace': namespace,
                   'quads': False,
                   'rdr': False,
                   'textIndex': False,
                   'truthMaintenance': False}

        # if self.has_namespace(namespace):
        #     raise IOError("Namespace already exists")
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

        log = logging.getLogger("%s.%s" % (self.log_name,
                                           inspect.stack()[0][3]))
        log.setLevel(self.log_level)

        url = self._make_url(namespace).replace("/sparql", "")
        result = requests.delete(url=url)
        if result.status_code == 200:
            log.critical(result.text)
            return result.text
        raise RuntimeError(result.text)

    def _make_url(self, namespace=None):
        """ Creates the REST Url based on the supplied namespace

        args:
            namespace: string of the namespace
        """
        rtn_url = self.url
        namespace = pick(namespace, self.namespace)
        if namespace:
            rtn_url = os.path.join(self.url.replace("sparql", ""),
                                   "namespace",
                                   namespace,
                                   "sparql").replace("\\", "/")
        elif not rtn_url.endswith("sparql"):
            rtn_url = os.path.join(self.url, "sparql").replace("\\", "/")
        return rtn_url

    def __repr__(self):
        return "<Blazegraph([{'host': '%s', 'namespace': '%s'}])>" % \
               (self.url, self.namespace)
