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
                                   make_list, p_args
from rdfframework.rdfdatatypes import rdfdatatypes as rdt
from rdfframework.sparql import run_sparql_query
from rdfframework.framework import RdfFramework
from rdfframework.rdfdatasets import RdfDataset
import rdfframework.rdfclass
from rdfframework.rdfclass import test
print("CONFIG ---------------------------------------------------------------")
#config = DictClass(config)
# pp.pprint(config)
print("----------------------------------------------------------------------")
CFG = RdfConfigManager(config=config)
NSM = RdfNsManager(config=CFG)
rdf_defs = CFG.RDF_DEFINITIONS
pyrdf = rdt.pyrdf
sparql = render_without_request("sparqlClassDefinitionList.rq",
                                 graph=CFG.RDF_DEFINITION_GRAPH,
                                 prefix=NSM.prefix())
x = run_sparql_query(sparql, namespace=CFG.RDF_DEFINITIONS.namespace)
#pp.pprint([pyrdf(item['kdsClass']) for item in x])
_sparql = render_without_request("sparqlClassDefinitionDataTemplate.rq",
                                 prefix=NSM.prefix(),
                                 item_uri="bf:Topic",
                                 graph=CFG.RDF_DEFINITION_GRAPH)
z = run_sparql_query(_sparql, namespace=rdf_defs.namespace)

sparqldefs = render_without_request("sparqlAllRDFClassDefs.rq",
                                 graph=CFG.RDF_DEFINITION_GRAPH,
                                 prefix=NSM.prefix())
# print(sparqldefs)
y = run_sparql_query(sparqldefs, namespace=rdf_defs.namespace)

# h = RdfDataset
# def group_classess(data, group_key="kdsClass"):
#     rtn_obj = {}
#     for row in data:
#         try:
#             rtn_obj[.append(row)
ds = RdfDataset()
ds.load_data(z, strip_orphans=True, obj_method="list")
# ds.classes
#print(json.dumps(ds, indent=4))
# RdfFramework(reset=True)
def test2(self, prop):
    return getattr(self, prop)

def print_doc(self=None):
    print(self.__doc__)

def find_values(field_list, data):
    return [(key, data.get(key)) for key in field_list if data.get(key)]

def string_wrap(string, width=80, indent=0):
    rtn_list = []
    line_list = []
    string = string.replace("\n"," ").replace("  ", " ")
    words = string.split(" ")
    line_len = indent
    if indent >0:
        line_list.append(" "*(indent-1))
    for word in words:
        if line_len + len(word) < width and len(word) < width:
            line_list.append(word)
            line_len += len(word) + 1
        elif len(word) >= width:
            rtn_list.append(word)
        else:
            rtn_list.append(" ".join(line_list))
            line_list = []
            if indent >0:
                line_list.append(" "*(indent-1))
            line_list.append(word)
            line_len = indent + len(word) + 1
    rtn_list.append(" ".join(line_list))
    return "\n".join(rtn_list)

def format_doc_vals(data,
                    descriptor,
                    seperator=": ",
                    divider=" | ",
                    subdivider=", ",
                    max_width=70,
                    indent=8,
                    subindent=4):
    line_data = []
    if descriptor:
        line_data.append("%s%s%s" %(" "*indent, descriptor, seperator))
    try:
        rtn_val = "%s%s%s" % (descriptor, seperator, data.pop(0)[1])
        if len(data) > 0 :
            rtn_val = "%s%s%s" % (rtn_val,
                                  divider,
                                  subdivider.join([item[1] for item in data]))
        rtn_val = string_wrap(rtn_val, max_width, indent)
    except IndexError:
        rtn_val =""
    return rtn_val


def make_doc_string(cls_def):
    label_fields = ['skos_prefLabel',
                    'schema_name',
                    'skos_altLabel',
                    'schema_alternateName',
                    'foaf_labelproperty',
                    'rdfs_label',
                    'hiddenlabel']
    description_fields = ['skos_definition',
                          'schema_description',
                          'rdfs_comment']
    note_fields = ['skos_note',
                   'schema_disambiguatingDescription']
    label = format_doc_vals(data=find_values(label_fields, cls_def),
                            descriptor="Label",
                            divider=" | ",
                            subdivider=", ")
    description = format_doc_vals(data=find_values(description_fields, cls_def),
                                  descriptor="Description",
                                  divider="",
                                  subdivider="\n")
    
    
    return "\n\n".join([label,description])



class RdfClassMeta(type):
    @property
    def doc(self):
        print_doc(self)

    @classmethod
    def __prepare__(*args, **kwargs):
        print('  RdfClassMeta.__prepare__(\n\t\t%s)' % (p_args(args, kwargs)))
        # pdb.set_trace()
        cls_defs = CFG.rdf_class_defs.get(args[1],{})
        doc_string = make_doc_string(cls_defs[args[1]])
        new_def = {}
    #     \
    # """ %s: %s --> %s
    #     ** autogenerated from knowledgelinks.io rdfframework rdf definitions

    #     attributes:
    #         %s""" % (args[1], 
    #                  cls_defs[args[1]].get('rdfs_label',''), 
    #                  cls_defs[args[1]].get('skos_definition',''),
    #                  "TBW")
        new_def['__doc__'] = doc_string
        new_def['doc'] = property(print_doc)
        return new_def



class RdfClassGenerator(object):
    def __init__(self):
        self.__get_defs()
        self.__make_defs()
        self.__make_classes()

    def __get_defs(self):
        sparqldefs = render_without_request("sparqlAllRDFClassDefs2.rq",
                                            graph=CFG.RDF_DEFINITION_GRAPH,
                                            prefix=NSM.prefix())
        print("Starting Class Def query")
        self.cls_defs_results = run_sparql_query(sparqldefs,
                                                 namespace=rdf_defs.namespace)
        print("Ending Class Def Query")
    def __make_defs(self):

        class_defs = {}
        for item in self.cls_defs_results:
            try:
                class_defs[item['RdfClass']['value']].append(item)
            except KeyError:
                class_defs[item['RdfClass']['value']] = [item]

        self.cls_defs = {NSM.pyuri(key):RdfDataset(value)
                         for key, value in class_defs.items()}
        CFG.__setattr__('rdf_class_defs', self.cls_defs, True)

    def __make_classes(self):
        # pdb.set_trace()
        for name in self.cls_defs.keys():
            setattr(rdfframework.rdfclass,
                    name, 
                    types.new_class(name,
                                    (dict,), 
                                    {'metaclass': RdfClassMeta}))

RdfClassGenerator()

test()
# import metalearning as m

# class bf_Topic(metaclass=m.Meta):
#      pass



