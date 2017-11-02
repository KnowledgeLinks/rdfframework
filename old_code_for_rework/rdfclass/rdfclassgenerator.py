__author__ = "Mike Stabile, Jeremy Nelson"

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
from rdfframework.sparql import run_sparql_query
from rdfframework.rdfdatasets import RdfDataset
from rdfframework.rdfclass import RdfClassBase
from rdfframework import rdfclass

# Setup Module logger

MNAME = pyfile_path(inspect.stack()[0][1])
MLOG_LVL = logging.DEBUG
logging.basicConfig(level=MLOG_LVL)
lg_r = logging.getLogger("requests")
lg_r.setLevel(logging.CRITICAL)

CFG = RdfConfigManager()
NSM = RdfNsManager()


class RdfClassGenerator(object):
    ln = "%s-RdfClassGenerator" % MNAME
    log_level = logging.DEBUG

    def __init__(self, reset=False, nsm=NSM, cfg=CFG):
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        lg.info("Starting")
        self.cfg = cfg
        self.nsm = nsm
        self.__get_defs(not reset)
        self.__make_defs()
        self.__make_classes()

    def __get_defs(self, cache=True):
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        lg.debug(" *** Started")
        if cache:
            lg.info("loading json cache")
            with open(
                os.path.join(self.cfg.CACHE_DATA_PATH,
                             "class_query.json")) as file_obj:
                self.cls_defs_results = json.loads(file_obj.read())

        if not cache or len(self.cls_defs_results) == 0:
            lg.info("NO CACHE, querying the triplestore")
            sparqldefs = render_without_request("sparqlAllRDFClassDefs2.rq",
                                                graph=self.cfg.RDF_DEFINITION_GRAPH,
                                                prefix=self.nsm.prefix())
            start = datetime.datetime.now()
            lg.info("Starting Class Def query")
            conn = self.cfg.def_tstore
            self.cls_defs_results = conn.query(sparqldefs)
            lg.info("query complete in: %s" % (datetime.datetime.now() - start))
            with open(
                os.path.join(self.cfg.CACHE_DATA_PATH, "class_query.json"),
                "w") as file_obj:
                file_obj.write(json.dumps(self.cls_defs_results, indent=4) )

    def __make_defs(self):
        """ Reads through the JSON object and converts them to Dataset """
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        start = datetime.datetime.now()
        lg.debug("Converting to a Dataset")

        class_defs = {}
        for item in self.cls_defs_results:
            try:
                class_defs[item['RdfClass']['value']].append(item)
            except KeyError:
                class_defs[item['RdfClass']['value']] = [item]
        self.cls_defs = {self.nsm.pyuri(key):RdfDataset(value,
                                                        def_load=True,
                                                        bnode_only=True)
                         for key, value in class_defs.items()}
        self.cfg.__setattr__('rdf_class_defs', self.cls_defs, True)
        lg.debug("conv complete in: %s" % (datetime.datetime.now() - start))

    def __make_classes(self):
        """ reads through the classes and generates an python class for each
        rdf:Class """
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        created = []
        lg.info("class length: %s" % len(self.cls_defs.keys()))
        lg.debug("create classes that are not subclassed")
        for name, cls_defs in self.cls_defs.items():
            # if name == 'bf_Topic': pdb.set_trace()
            if not self.cls_defs[name][name].get('rdfs_subClassOf'):
                created.append(name)
                setattr(rdfclass,
                        name,
                        types.new_class(name,
                                        (RdfClassBase,),
                                        {#'metaclass': RdfClassMeta,
                                         'cls_defs': cls_defs}))
        lg.debug("created classes:\n%s", created)
        for name in created:
            del self.cls_defs[name]
        left = len(self.cls_defs.keys())
        classes = []
        while left > 0:
            new = []
            for name, cls_defs in self.cls_defs.items():
                parents = self.cls_defs[name][name].get('rdfs_subClassOf')
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
                    del self.cls_defs[name]
                except KeyError:
                    pass
            if left == len(self.cls_defs.keys()):
                c_list = [self.cls_defs[name][name].get('rdfs_subClassOf') \
                          for name in self.cls_defs.keys()]
                classess = []
                for cl in c_list:
                    for item in cl:
                        classes.append(item)

                for name in self.cls_defs.keys():
                    if name in classes:
                        classes.remove(name)
            left = len(self.cls_defs.keys())
