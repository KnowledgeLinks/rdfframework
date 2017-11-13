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

from rdfframework.utilities import render_without_request, make_list, \
        pyfile_path, pp, RDF_CLASSES, INFERRED_CLASS_PROPS
from rdfframework.rdfdatatypes import BaseRdfDataType, pyrdf, Uri
from rdfframework.rdfdatasets import RdfDataset
from rdfframework.rdfclass import RdfClassBase, make_property, link_property
from rdfframework import rdfclass
from rdfframework.configuration import RdfConfigManager, RdfNsManager

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
        self.def_sparql = sparql_template #
        self.cache_filepath = os.path.join(self.cfg.CACHE_DATA_PATH,
                                           self.cache_file)
        self.get_defs(not reset)
        self.conv_defs()
        self.make()
        setattr(self.cfg, "props_initialized", True)
        log.info(" completed in %s", (datetime.datetime.now() - start))

    def get_defs(self, cache=True):
        """ Gets the defitions

        args:
            cache: True will read from the file cache, False queries the
                   triplestore
        """
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

        # self.cfg.__setattr__('rdf_prop_defs', self.defs, True)
        log.debug(" conv complete in: %s" % (datetime.datetime.now() - start))

class RdfPropertyFactory(RdfBaseFactory):
    """ Extends RdfBaseFactory for property creation specific querying """
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
            make_property(self.defs[prop], prop, [])
        log.info(" property count: %s", len(prop_list))

class RdfClassFactory(RdfBaseFactory):
    """ Extends RdfBaseFactory to property creation specific querying """
    lg_name = "%s-RdfClassFactory" % MNAME
    log_level = logging.DEBUG #MLOG_LVL #
    cache_file = "classes.json"
    classes_key = set([Uri(item) for item in RDF_CLASSES])
    inferred_key = set([Uri(item) for item in INFERRED_CLASS_PROPS])
    rdf_type = Uri('rdf_type')

    def __init__(self, conn, reset=False, nsm=NSM, cfg=CFG):
        if cfg.props_initialized != True:
            err_msg = ["RdfPropertyFactory must be run prior to",
                       "the intialization of RdfClassFactory!"]
            raise RuntimeError(" ".join(err_msg))
        sparql_template = "sparqlDefinitionClassesAll.rq"
        super().__init__(conn, sparql_template, reset, nsm, cfg)

    def make(self):
        """ reads through the definitions and generates an python class for each
        definition """
        log = logging.getLogger("%s.%s" % (self.lg_name, inspect.stack()[0][3]))
        log.setLevel(self.log_level)
        created = []
        self.set_class_dict()
        start = datetime.datetime.now()
        log.info(" # of classes to create: %s" % len(self.class_dict))
        log.debug(" creating classes that are not subclassed")
        for name, cls_defs in self.class_dict.items():
            if not self.class_dict[name].get('rdfs_subClassOf'):
                created.append(name)
                setattr(rdfclass,
                        name,
                        types.new_class(name,
                                        (RdfClassBase,),
                                        {#'metaclass': RdfClassMeta,
                                         'cls_defs': cls_defs}))
        log.debug(" created %s classes in: %s",
                  len(created),
                  (datetime.datetime.now() - start))
        for name in created:
            del self.class_dict[name]
        left = len(self.class_dict)
        classes = []
        while left > 0:
            new = []
            for name, cls_defs in self.class_dict.items():
                parents = self.class_dict[name].get('rdfs_subClassOf')
                for parent in make_list(parents):
                    bases = tuple()
                    if parent in created or parent in classes:
                        if parent in classes:
                            bases += (RdfClassBase, )
                        else:
                            base = getattr(rdfclass, parent)
                            bases += (base,) + base.__bases__
                if len(bases) > 0:
                    created.append(name)
                    setattr(rdfclass,
                            name,
                            types.new_class(name,
                                            bases,
                                            {#'metaclass': RdfClassMeta,
                                             'cls_defs': cls_defs}))
            for name in created:
                try:
                    del self.class_dict[name]
                except KeyError:
                    pass
            if left == len(self.class_dict):
                c_list = [self.class_dict[name].get('rdfs_subClassOf') \
                          for name in self.class_dict]
                classess = []
                for cl in c_list:
                    for item in cl:
                        classes.append(item)

                for name in self.class_dict:
                    if name in classes:
                        classes.remove(name)
            left = len(self.class_dict)
        # self.tie_properties(created)
        log.info(" created all classes in %s",
                 (datetime.datetime.now() - start))
    def set_class_dict(self):
        """ Reads through the dataset and assigns self.class_dict the key value
            pairs for the classes in the dataset
        """

        self.class_dict = {}
        for name, cls_defs in self.defs.items():
            def_type = set(cls_defs.get(self.rdf_type, []))
            # a class can be determined by checking to see if it is of an
            # rdf_type listed in the classes_key or has a property that is
            # listed in the inferred_key
            if def_type.intersection(self.classes_key) or \
                    list([cls_defs.get(item) for item in self.inferred_key]):
                self.class_dict[name] = cls_defs

    def tie_properties(self, class_list):
        """ Runs through the classess and ties the properties to the class

        args:
            class_list: a list of class names to run
        """
        log = logging.getLogger("%s.%s" % (self.lg_name, inspect.stack()[0][3]))
        log.setLevel(self.log_level)
        start = datetime.datetime.now()
        log.info(" Tieing properties to the class")
        for cls_name in class_list:
            cls_obj = getattr(rdfclass, cls_name)
            prop_dict = dict(cls_obj.properties)
            for prop_name, prop_obj in cls_obj.properties.items():
                setattr(cls_obj, prop_name, link_property(prop_obj, cls_obj))
        log.info(" Finished tieing properties in: %s",
                 (datetime.datetime.now() - start))
