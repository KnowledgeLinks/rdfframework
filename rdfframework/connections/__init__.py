import logging
import inspect
from .blazegraph import Blazegraph
from .rdflibconn import RdflibConn
from .triplestoreconn import TriplestoreConnection
import rdfframework.utilities

__MNAME__ = rdfframework.utilities.pyfile_path(inspect.stack()[0][1])
__LOG_LEVEL__ = logging.INFO

def make_tstore_conn(self, params):
    """ Returns a triplestore connection

        args:
            attr_name: The name the connection will be assigned in the
                config manager
            params: The paramaters of the connection

        kwargs:
            log_level: logging level to use
    """
    log = logging.getLogger("%s.%s" % (__MNAME__,
                                       inspect.stack()[0][3]))
    log.setLevel(kwargs.get('log_level', __LOG_LEVEL__))
    vendor_dict = {"blazegraph": Blazegraph,
                   "rdflib": RdflibConn}
    try:
        vendor = TriplestoreConnection[params.get('vendor')]
    except KeyError:
        vendor = TriplestoreConnection['blazegraph']
    conn = vendor(local_directory=params.get("local_directory"),
                  url=params.get("url"),
                  container_dir=params.get("container_dir"),
                  namespace=params.get("namespace"),
                  namespace_params=params.get('namespace_params', {}))
    if not conn.has_namespace(conn.namespace):
        log.warn("namespace '%s' does not exist. Creating namespace",
                 conn.namespace)
        conn.create_namespace(conn.namespace)
    return conn

def setup_conn(**kwargs):
    """ returns a triplestore conncection based on the kwargs.
    Order of preceedence is as follows:
        kwargs['conn']
        kwargs['tstore_def']
        kwargs['triplestore_url']
        kwargs['rdflib']
        RdfConfigManager.data_tstore
        RdfConfigManager.TRIPLESTORE_URL

    kwargs:
        conn: established triplestore connection object
        tstore_def: dictionary of paramaters specifying the connection as
                outlined in the config file
        triplestore_url: url to a triplestore. A blazegraph connection
            will be used if specified
        rdflib: defintion for an rdflib connection
    """
    from rdfframework.configuration import RdfConfigManager
    if kwargs.get("conn"):
        conn = kwargs['conn']
    elif kwargs.get("tstore_def"):
        conn = make_tstore_conn(kwargs['tstore_def'])
    elif kwargs.get("triplestore_url"):
        conn = TriplestoreConnection['blazegraph'](kwargs['triplestore_url'])
    elif kwargs.get("rdflib"):
        conn = TriplestoreConnection['rdflib'](kwargs.get('rdflib'))
    elif RdfConfigManager().data_tstore and \
            not isinstance(RdfConfigManager().data_tstore,
                           rdfframework.utilities.EmptyDot):
        conn = RdfConfigManager().data_tstore
    elif RdfConfigManager().TRIPLESTORE_URL and \
            not isinstance(RdfConfigManager().TRIPLESTORE_URL,
                           rdfframework.utilities.EmptyDot):
        conn = TriplestoreConnection['blazegraph'](\
                RdfConfigManager().TRIPLESTORE_URL)
    else:
        conn = TriplestoreConnection['blazegraph']()
    return conn
