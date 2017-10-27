""" Modules contains factories for generating rdf classes and properties """

import os
import pdb
import pprint
import json
import types
import inspect
import logging
import datetime
from hashlib import sha1

from rdfframework.utilities import RdfNsManager, render_without_request, \
                                   RdfConfigManager, make_list, pp, pyfile_path
from rdfframework.rdfdatatypes import BaseRdfDataType, pyrdf
from rdfframework.rdfdatasets import RdfDataset
from rdfframework.rdfclass import RdfClassBase, make_property
from rdfframework import rdfclass

__author__ = "Mike Stabile, Jeremy Nelson"

# Setup Module logger

MNAME = pyfile_path(inspect.stack()[0][1])
MLOG_LVL = logging.INFO
logging.basicConfig(level=MLOG_LVL)
lg_r = logging.getLogger("requests")
lg_r.setLevel(logging.CRITICAL)

CFG = RdfConfigManager()
NSM = RdfNsManager()


class RdfBaseFactory(object):
    lg_name = "%s-RdfBaseGenerator" % MNAME
    log_level = MLOG_LVL #logging.DEBUG
    cache_file = "base.json"
    cache_filepath = ""

    def __init__(self, conn, sparql_template, reset=False, nsm=NSM, cfg=CFG):
        log = logging.getLogger("%s.%s" % (self.lg_name, inspect.stack()[0][3]))
        log.setLevel(self.log_level)
        start = datetime.datetime.now()
        log.info(" Starting")
        self.conn = conn
        self.cfg = cfg
        self.nsm = nsm
        self.def_sparql = sparql_template #"sparqlDefinitionPropertiesAll.rq"
        self.cache_filepath = os.path.join(self.cfg.CACHE_DATA_PATH,
                                           self.cache_file)
        self.get_defs(not reset)
        self.conv_defs()
        self.make()
        setattr(self.cfg, "props_initialized", True)
        log.info(" completed in %s", (datetime.datetime.now() - start))

    def get_defs(self, cache=True):
        log = logging.getLogger("%s.%s" % (self.lg_name, inspect.stack()[0][3]))
        log.setLevel(self.log_level)
        log.debug(" *** Started")
        if cache:
            log.info(" loading json cache")
            try:
                with open(self.cache_filepath) as file_obj:
                    self.results = json.loads(file_obj.read())
            except FileNotFoundError:
                self.results = []
        if not cache or len(self.results) == 0:
            log.info(" NO CACHE, querying the triplestore")
            sparql = render_without_request(self.def_sparql,
                                            graph=self.conn.graph,
                                            prefix=self.nsm.prefix())
            start = datetime.datetime.now()
            log.info(" Starting query")
            self.results = self.conn.query(sparql)
            log.info("query complete in: %s | %s triples retrieved.",
                     (datetime.datetime.now() - start),
                     len(self.results))
            with open(self.cache_filepath, "w") as file_obj:
                file_obj.write(json.dumps(self.results, indent=4))

    def conv_defs(self):
        """ Reads through the JSON object and converts them to Dataset """
        log = logging.getLogger("%s.%s" % (self.lg_name, inspect.stack()[0][3]))
        log.setLevel(self.log_level)
        start = datetime.datetime.now()
        log.debug(" Converting to a Dataset: %s Triples", len(self.results))
        self.defs = RdfDataset(self.results,
                               def_load=True,
                               bnode_only=True)

        self.cfg.__setattr__('rdf_prop_defs', self.defs, True)
        log.debug(" conv complete in: %s" % (datetime.datetime.now() - start))

    # def make(self):
    #     """ place holder method for subclasses """
    #     pass


class RdfPropertyFactory(RdfBaseFactory):
    """ Extends RdfBaseFactory to property creation specific querying """
    lg_name = "%s-RdfPropertyFactory" % MNAME
    log_level = MLOG_LVL #logging.DEBUG
    cache_file = "properties.json"

    def __init__(self, conn, reset=False, nsm=NSM, cfg=CFG):
        sparql_template = "sparqlDefinitionPropertiesAll.rq"
        super().__init__(conn, sparql_template, reset, nsm, cfg)

    def make(self):
        """ reads through the definitions and generates an python class for each
        definition """
        log = logging.getLogger("%s.%s" % (self.lg_name, inspect.stack()[0][3]))
        log.setLevel(self.log_level)
        created = []
        prop_list = [item for item in self.defs if item.type == 'uri']
        log.debug(" creating properties ... ")
        for prop in prop_list:
            make_property(self.defs[prop], prop, "")
        log.info(" property count: %s", len(prop_list))

class RdfClassFactory(RdfBaseFactory):
    """ Extends RdfBaseFactory to property creation specific querying """
    lg_name = "%s-RdfClassFactory" % MNAME
    log_level = MLOG_LVL #logging.DEBUG
    cache_file = "classes.json"

    def __init__(self, conn, reset=False, nsm=NSM, cfg=CFG):
        if cfg.props_initialized != True:
            raise RuntimeError("RdfPropertyFactory must be run prior!")
        sparql_template = "sparqlDefinitionClassesAll.rq"
        super().__init__(conn, sparql_template, reset, nsm, cfg)

    def make(self):
        """ reads through the definitions and generates an python class for each
        definition """
        pass
