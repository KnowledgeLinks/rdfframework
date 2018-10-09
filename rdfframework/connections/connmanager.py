import inspect
import time
import logging
import requests

from rdfframework.utilities import (KeyRegistryMeta,
                                    initialized,
                                    EmptyDot)
from elasticsearch import Elasticsearch
import pdb, pprint

__LOG_LEVEL__ = logging.INFO

class RdfwConnections(metaclass=KeyRegistryMeta):
    __required_idx_attrs__ = {'vendor', 'conn_type'}
    __nested_idx_attrs__ = {"conn_type"}
    delay_check = None

    def __repr__(self):
        if self.__class__ == RdfwConnections:
            return "<RdfwConnections: %s" % pprint.pformat(self.__registry__)
        attrs = ['namespace', 'active', 'check_status']
        msg_attrs = ["'%s': '%s'" % (attr, getattr(self, attr))
                     for attr in attrs
                     if hasattr(self, attr)]
        url = self.ext_url
        if self.url:
            url = self.url
        msg_attrs = ["url: %s" % url] + msg_attrs
        return "<%s([{%s}])>" % (self.vendor.capitalize(), ", ".join(msg_attrs))

    def __set_mgr__(self, **kwargs):
        """ set the data file management for the connection

        kwargs:
            data_file_manager: instance of DataFileManager
            data_upload: list of tuples describing the files to upload
        """
        self.mgr = None
        # if kwargs.get("data_upload"):
        import rdfframework.datamanager as dm
        log.info("Setting Data Manager for conn '%s'", kwargs.get('name'))
        mgr = kwargs.get('data_file_manager', kwargs.get("name", True))
        if isinstance(mgr, dm.DataFileManager):
            self.mgr = mgr
        elif mgr == 'active_defs':
            self.mgr = dm.DefinitionManager(conn=self, **kwargs)
        elif mgr == 'datastore':
            self.mgr = dm.DatastoreManager(conn=self, **kwargs)
        else:
            self.mgr = dm.DataFileManager(conn=self, **kwargs)
        if self.mgr: # and kwargs.get('data_upload'):
            self.mgr.add_file_locations(kwargs.get('data_upload',[]))
            if kwargs.get("delay_check"):
                self.delay_check = kwargs
            else:
                if self.check_status:
                    # kwargs['log_level'] = logging.DEBUG
                    self.mgr.load(**kwargs)
                else:
                    log.warn("conn '%s' check_status failed",
                             kwargs.get('name'))

    def delay_check_pass(self):
        if self.delay_check:
            try:
                self.mgr.load(**self.delay_check)
            except AttributeError:
                pass
            self.delay_check = None

class ConnManagerMeta(type):
    """ Metaclass ensures that there is only one instance of the RdfConnManager
    """

    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(ConnManagerMeta,
                                        cls).__call__(*args, **kwargs)
        else:
            conns = None
            if args:
                conns = args[0]
            elif 'connections' in kwargs:
                conns = kwargs['connections']
            if conns:
                cls._instances[cls].load(conns, **kwargs)
        return cls._instances[cls]

    def clear(cls):
        cls._instances = {}

class ConnManager(metaclass=ConnManagerMeta):
    """ class for managing database connections """
    log_level = logging.INFO
    conn_mapping = RdfwConnections
    __is_initialized__ = False

    def __init__(self, connections=None, **kwargs):
        self.conns = {}
        self.log_level = kwargs.get('log_level', self.log_level)
        if connections:
            self.load(connections, **kwargs)

    def set_conn(self, **kwargs):
        """ takes a connection and creates the connection """

        # log = logging.getLogger("%s.%s" % (self.log, inspect.stack()[0][3]))
        log.setLevel(kwargs.get('log_level',self.log_level))

        conn_name = kwargs.get("name")
        if not conn_name:
            raise NameError("a connection requires a 'name': %s" % kwargs)
        elif self.conns.get(conn_name):
            raise KeyError("connection '%s' has already been set" % conn_name)

        if not kwargs.get("active", True):
            log.warning("Connection '%s' is set as inactive" % conn_name)
            return
        conn_type = kwargs.get("conn_type")
        if not conn_type or conn_type not in self.conn_mapping.nested:
            err_msg = ["a connection requires a valid 'conn_type':\n",
                       "%s"]
            raise NameError("".join(err_msg) % (list(self.conn_mapping.nested)))
        log.info("Setting '%s' connection", conn_name)
        if conn_type == "triplestore":
            conn = make_tstore_conn(kwargs)
        else:
            conn = RdfwConnections[conn_type][kwargs['vendor']](**kwargs)
        self.conns[conn_name] = conn
        self.__is_initialized__ = True

    @initialized
    def get(self, conn_name, default=None, **kwargs):
        """ returns the specified connection

        args:
            conn_name: the name of the connection
        """

        if isinstance(conn_name, RdfwConnections):
            return conn_name
        try:
            return self.conns[conn_name]
        except KeyError:
            if default:
                return self.get(default, **kwargs)
            raise LookupError("'%s' connection has not been set" % conn_name)

    def load(self, conn_list, **kwargs):
        """ Takes a list of connections and sets them in the manager

        args:
            conn_list: list of connection defitions
        """
        for conn in conn_list:
            conn['delay_check'] = kwargs.get('delay_check', False)
            self.set_conn(**conn)
        if kwargs.get('delay_check'):
            test = self.wait_for_conns(**kwargs)
            if not test:
                log.critical("\n\nEXITING:Unable to establish connections \n"
                             "%s", test)

    @property
    def failing(self):
        """ Tests to see if all connections are working

        returns:
            dictionary of all failing connections
        """
        log_levels = {key: conn.log_level for key, conn in self.conns.items()
                      if hasattr(conn, 'log_level')}
        for key in log_levels:
            self.conns[key].log_level = logging.CRITICAL
        failing_conns = {key: conn for key, conn in self.active.items()
                         if not conn.check_status}
        for key, level in log_levels.items():
            self.conns[key].log_level = level
        return failing_conns

    def wait_for_conns(self, timeout=60, start_delay=0, interval=5, **kwargs):
        ''' delays unitil all connections are working

            args:
                timeout: number of seconds to try to connecting. Error out when
                        timeout is reached
                start_delay: number of seconds to wait before checking status
                interval: number of seconds to wait between checks
        '''
        log.setLevel(kwargs.get('log_level',self.log_level))
        timestamp = time.time()
        last_check = time.time() + start_delay - interval
        last_delay_notification = time.time() - interval
        timeout += 1
        failing = True
        up_conns = {}
        # loop until the server is up or the timeout is reached
        while((time.time()-timestamp) < timeout) and failing:
            # if delaying, the start of the check, print waiting to start
            if start_delay > 0 and time.time() - timestamp < start_delay \
                    and (time.time()-last_delay_notification) > 5:
                print("Delaying server status check until %ss. Current time: %ss" \
                        % (start_delay, int(time.time() - timestamp)))
                last_delay_notification = time.time()
            # check status at the specified 'interval' until the server is up
            first_check = True
            while ((time.time()-last_check) > interval) and failing:
                msg = ["\tChecked status of servers at %ss" % \
                        int((time.time()-timestamp)),
                       "\t** CONNECTION STATUS:"]
                last_check = time.time()
                failing = self.failing
                new_up = (self.active.keys() - failing.keys()) - \
                          up_conns.keys()
                msg += ["\t\t UP - %s: %s" % (key, self.conns[key])
                       for key in new_up]
                up_conns.update({key: self.conns[key] for key in new_up})
                msg.append("\t*** '%s' connection(s) up" % len(up_conns))
                msg += ["\t\t FAILING - %s: %s" % (key, self.conns[key])
                        for key in failing]
                log.info("** CONNECTION STATUS:\n%s", "\n".join(msg))
                if not failing:
                    log.info("**** Servers up at %ss" % \
                        int((time.time()-timestamp)))
                    break
        if failing:
            raise RuntimeError("Unable to establish connection(s): ",
                               failing)
        for conn in up_conns.values():
            conn.delay_check_pass()
        return not failing

    @property
    def list_conns(self):
        """ returns a list of established connections """
        return list(self.conns)

    def __getattr__(self, attr):
        return self.get(attr)

    def __getitem__(self, item):
        return self.get(item)

    def __iter__(self):
        return iter(self.conns.items())

    def __repr__(self):
        rtn_val = super().__repr__()
        conns = "\n\t".join(sorted(["%s: %s" % (key.ljust(16,' '),
                                                value.__repr__()[:60])
                                    for key, value in self.conns.items()]))
        return "{standard}\n\t{conns}".format(standard=rtn_val,
                                              conns=conns)

    @property
    def active(self):
        """ returns a dictionary of connections set as active.
        """
        return {key: value for key, value in self.conns.items()
                if value.active}

def make_tstore_conn(params, **kwargs):
    """ Returns a triplestore connection

        args:
            attr_name: The name the connection will be assigned in the
                config manager
            params: The paramaters of the connection

        kwargs:
            log_level: logging level to use
    """
    log.setLevel(params.get('log_level', __LOG_LEVEL__))
    log.debug("\n%s", params)
    params.update(kwargs)
    try:
        vendor = RdfwConnections['triplestore'][params.get('vendor')]
    except KeyError:
        vendor = RdfwConnections['triplestore']['blazegraph']
    conn = vendor(**params)
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
        conn = RdfwConnections['triplestore']['blazegraph']( \
                kwargs['triplestore_url'])
    elif kwargs.get("rdflib"):
        conn = RdfwConnections['triplestore']['rdflib'](kwargs.get('rdflib'))
    elif RdfConfigManager().data_tstore and \
            not isinstance(RdfConfigManager().data_tstore, EmptyDot):
        conn = ConnManager().datastore
    elif RdfConfigManager().TRIPLESTORE_URL and \
            not isinstance(RdfConfigManager().TRIPLESTORE_URL, EmptyDot):
        conn = RdfwConnections['triplestore']['blazegraph'](\
                RdfConfigManager().TRIPLESTORE_URL)
    else:
        conn = RdfwConnections['triplestore']['blazegraph']()
    return conn
