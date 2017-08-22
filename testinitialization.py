"""    This module is used for setting an intial test configs and values for 
the rdfframework """

import sys
import os
import pdb
import pprint
import json
import types
import inspect

PACKAGE_BASE = os.path.abspath(
    os.path.split(
        os.path.dirname(__file__))[0])
print("PACKAGE_BASE: ", PACKAGE_BASE)
sys.path.append(PACKAGE_BASE)
from testconfig import config
from rdfframework.utilities import DictClass, pp, RdfNsManager, pp, \
                                   render_without_request, RdfConfigManager, \
                                   make_list, p_args, string_wrap, \
                                   make_doc_string, format_doc_vals
from rdfframework.rdfdatatypes import rdfdatatypes as rdt
from rdfframework.sparql import run_sparql_query
from rdfframework.framework import RdfFramework
from rdfframework.rdfdatasets import RdfDataset
import rdfframework.rdfclass
r = rdfframework.rdfclass

print("CONFIG ---------------------------------------------------------------")
#config = DictClass(config)
# pp.pprint(config)
print("----------------------------------------------------------------------")
CFG = RdfConfigManager(config=config)
NSM = RdfNsManager(config=CFG)
rdf_defs = CFG.RDF_DEFINITIONS
pyrdf = rdt.pyrdf

def print_doc(self=None):
    print(self.__doc__)



def get_properties(cls_def):
    """ cycles through the class definiton and returns all properties """

    prop_list = {prop: value for prop, value in cls_def.items() \
                 if 'rdf_Property' in value.get('rdf_type',"") }

    return prop_list

class RegistryMeta(type):
    def __getitem__(meta, key):
        try:
            return meta._registry[key]
        except KeyError:
            return []

class Registry(type, metaclass=RegistryMeta):
    _registry = {}

    def __new__(meta, name, bases, clsdict):
        cls = super(Registry, meta).__new__(meta, name, bases, clsdict)
        if len(bases[:-1]) > 0:
            try:
                meta._registry[bases[0].__name__].append(cls)
            except KeyError:
                meta._registry[bases[0].__name__] = [cls]
        return cls

class RdfPropertyMeta(type):
    @classmethod
    def __prepare__(*args, **kwargs):
        # print('  RdfClassMeta.__prepare__(\n\t\t%s)' % (p_args(args, kwargs)))
        # pdb.set_trace()
        prop_defs = kwargs.pop('prop_defs')
        new_def = prop_defs
        new_def['_data'] = []
        return new_def

    def __new__(meta, name, bases, clsdict, **kwds):
        return super().__new__(meta, name, bases, clsdict)

    def __init__(self, *args, **kwargs):
        pass

class RdfPropertyBase(): #  metaclass=RdfPropertyMeta):
    @property
    def test(self):
        print('test')

def make_property(prop_defs, prop_name, cls_name):
    """ Generates a property class from the defintion dictionary

        args:
            prop_def: the dictionary defining the property
            cls_name: the name of the rdf_class with which the property is 
                      associated
    """

    return types.new_class("%s_%s" % (prop_name, cls_name),
                           (RdfPropertyBase, dict,),
                           {'metaclass': RdfPropertyMeta,
                            'prop_defs': prop_defs})

class RdfClassMeta(Registry):

    @property
    def doc(self):  
        print_doc(self)

    

    @classmethod
    def __prepare__(*args, **kwargs):
        # print('  RdfClassMeta.__prepare__(\n\t\t%s)' % (p_args(args, kwargs)))
        # pdb.set_trace()
        try:
            cls_defs = kwargs.pop('cls_defs') #CFG.rdf_class_defs.get(args[1],{})
            props = get_properties(cls_defs)
            doc_string = make_doc_string(args[1],
                                        cls_defs[args[1]],
                                        args[2],
                                        props)
            new_def = {}
            new_def['__doc__'] = doc_string
            new_def['doc'] = property(print_doc)
            new_def['json_def'] = cls_defs
            new_def['properties'] = props.keys()
            new_def['id'] = None
            
            for prop, value in props.items():
                new_def[prop] = make_property(value, prop, args[1])
            return new_def
        except KeyError:
            return {}

    def __new__(meta, name, bases, clsdict, **kwds):
        return super().__new__(meta, name, bases, clsdict)

    def __init__(self, *args, **kwargs):
        pass

class RdfClassBase(dict, metaclass=RdfClassMeta):
    def __init__(self, *args, **kwargs):
        pass

    def subclasses(self):
        return Registry[self.__class__.__name__]


class RdfClassGenerator(object):
    def __init__(self, nsm=NSM, cfg=CFG):
        self.cfg = cfg
        self.nsm = nsm
        self.__get_defs()
        self.__make_defs()
        self.__make_classes()

    def __get_defs(self, cache=True):
        if cache:
            with open(
                os.path.join(self.cfg.JSON_LOCATION, "class_query.json")) as file_obj:
                self.cls_defs_results = json.loads(file_obj.read())
        else:
            sparqldefs = render_without_request("sparqlAllRDFClassDefs2.rq",
                                                graph=self.cfg.RDF_DEFINITION_GRAPH,
                                                prefix=self.nsm.prefix())
            print("Starting Class Def query")
            self.cls_defs_results = run_sparql_query(sparqldefs,
                    namespace=rdf_defs.namespace)
            print("Ending Class Def Query")
            with open(
                os.path.join(self.cfg.JSON_LOCATION,"class_query.json"),
                "w") as file_obj:
                file_obj.write(json.dumps(self.cls_defs_results, indent=4) )

    def __make_defs(self):

        class_defs = {}
        for item in self.cls_defs_results:
            try:
                class_defs[item['RdfClass']['value']].append(item)
            except KeyError:
                class_defs[item['RdfClass']['value']] = [item]

        self.cls_defs = {self.nsm.pyuri(key):RdfDataset(value)
                         for key, value in class_defs.items()}
        self.cfg.__setattr__('rdf_class_defs', self.cls_defs, True)

    def __make_classes(self):
        # pdb.set_trace()
        # set the all the base classes
        created = []
        print("class len: ", len(self.cls_defs.keys()))
        for name, cls_defs in self.cls_defs.items():
            if not self.cls_defs[name][name].get('rdfs_subClassOf'):
                created.append(name)
                setattr(rdfframework.rdfclass,
                        name,
                        types.new_class(name,
                                        (RdfClassBase,),
                                        {#'metaclass': RdfClassMeta,
                                         'cls_defs': cls_defs}))
        for name in created:
            del self.cls_defs[name]
        left = len(self.cls_defs.keys())
        classes = []
        while left > 0:
            new = []
            for name, cls_defs in self.cls_defs.items():
                parents = self.cls_defs[name][name].get('rdfs_subClassOf')
                # pdb.set_trace()
                for parent in make_list(parents):
                    bases = tuple()
                    if parent in created or parent in classes:
                        if parent in classes:
                            bases += (RdfClassBase, )
                        else:
                            base = getattr(rdfframework.rdfclass,
                                            parent)
                            bases += (base,) + base.__bases__
                if len(bases) > 0:
                    created.append(name)
                    setattr(rdfframework.rdfclass,
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
                classes = [self.cls_defs[name][name].get('rdfs_subClassOf') for
                           name in self.cls_defs.keys()]
                for name in self.cls_defs.keys():
                    if name in classes:
                        classes.remove(name)
            left = len(self.cls_defs.keys())


RdfClassGenerator()

# sparql = render_without_request("sparqlClassDefinitionList.rq",
#                                  graph=CFG.RDF_DEFINITION_GRAPH,
#                                  prefix=NSM.prefix())
# x = run_sparql_query(sparql, namespace=CFG.RDF_DEFINITIONS.namespace)
# #pp.pprint([pyrdf(item['kdsClass']) for item in x])
# _sparql = render_without_request("sparqlClassDefinitionDataTemplate.rq",
#                                  prefix=NSM.prefix(),
#                                  item_uri="bf:Topic",
#                                  graph=CFG.RDF_DEFINITION_GRAPH)
# z = run_sparql_query(_sparql, namespace=rdf_defs.namespace)

# sparqldefs = render_without_request("sparqlAllRDFClassDefs.rq",
#                                  graph=CFG.RDF_DEFINITION_GRAPH,
#                                  prefix=NSM.prefix())
# # print(sparqldefs)
# y = run_sparql_query(sparqldefs, namespace=rdf_defs.namespace)

# # h = RdfDataset
# # def group_classess(data, group_key="kdsClass"):
# #     rtn_obj = {}
# #     for row in data:
# #         try:
# #             rtn_obj[.append(row)
# ds = RdfDataset()
# ds.load_data(z, strip_orphans=True, obj_method="list")
# # ds.classes
# #print(json.dumps(ds, indent=4))
# # RdfFramework(reset=True)


sparql = render_without_request("sparqlAllItemDataTemplate.rq",
                                item_uri="<http://library.kean.edu/10#Work>",
                                prefix=NSM.prefix())
x = run_sparql_query(sparql, namespace="kean_marc")
#pp.pprint([pyrdf(item['kdsClass']) for item in x])



