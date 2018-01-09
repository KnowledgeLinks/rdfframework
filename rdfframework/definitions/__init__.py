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
    log = "%s:RdfConnManager" % __MNAME__
    log_level = logging.INFO
    is_initialized = False
    vocab_map = {
        "rdf": {
            "filename": rdf.ttl,
            "download": "https://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "namespace": "https://www.w3.org/1999/02/22-rdf-syntax-ns#"
        },
        "owl": {
            "filename": owl.ttl,
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

    def __init__(self, vocabularies=None, **kwargs):
        self.__vocabs__ = {}
        self.log_level = kwargs.get('log_level', self.log_level)
        if vocabularies:
            self.load(vocabularies, **kwargs)

    def set_vocab(self, **kwargs):
        """ takes a connection and creates the connection """

        log = logging.getLogger("%s.%s" % (self.log, inspect.stack()[0][3]))
        log.setLevel(kwargs.get('log_level',self.log_level))

        conn_name = kwargs.get("name")
        if not conn_name:
            raise NameError("a connection requires a 'name': %s" % kwargs)
        elif self.conns.get(conn_name):
            raise KeyError("connection '%s' has already been set" % conn_name)

        if not kwargs.get("active", True):
            log.warn("Connection '%s' is set as inactive" % conn_name)
            return
        conn_type = kwargs.get("conn_type")
        if not conn_type or conn_type not in self.conn_mapping.nested:
            err_msg = ["a connection requires a valid 'conn_type':\n",
                       "%s"]
            raise NameError("".join(err_msg) % (list(self.conn_mapping.nested)))
        if conn_type == "triplestore":
            conn = make_tstore_conn(kwargs)
        else:
            conn = RdfwConnections[conn_type][kwargs['vendor']](**kwargs)
        self.conns[conn_name] = conn
        self.is_initialized = True

    @initialized
    def get(self, conn_name, **kwargs):
        """ returns the specified connection

        args:
            conn_name: the name of the connection
        """
        try:
            return self.conns[conn_name]
        except KeyError:
            raise LookupError("'%s' connection has not been set" % conn_name)

    def load(self, conn_list, **kwargs):
        """ Takes a list of connections and sets them in the manager

        args:
            conn_list: list of connection defitions
        """
        for conn in conn_list:
            # pdb.set_trace()
            conn['delay_check'] = kwargs.get('delay_check', False)
            self.set_conn(**conn)

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
        failing_conns = {key: conn for key, conn in self.conns.items()
                         if not conn.check_status}
        for key, level in log_levels.items():
            self.conns[key].log_level = level
        return failing_conns

    def wait_for_conns(self, timeout=10, start_delay=0, interval=5, **kwargs):
        ''' delays unitil all connections are working

            args:
                timeout: number of seconds to try to connecting. Error out when
                        timeout is reached
                start_delay: number of seconds to wait before checking status
                interval: number of seconds to wait between checks
        '''
        log = logging.getLogger("%s.%s" % (self.log, inspect.stack()[0][3]))
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
                new_up = (self.conns.keys() - failing.keys()) - up_conns.keys()
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
        return not failing


    def list_conns(self):
        """ returns a list of established connections """
        return list(self.conns)

    def __getattr__(self, attr):
        return self.get_conn(attr)

    def __getitem__(self, item):
        return self.get_conn(item)

    def __iter__(self):
        return iter(cls._ns_instances)
