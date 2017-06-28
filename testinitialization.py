"""    This module is used for setting an intial test configs and values for 
the rdfframework """

import sys
import os
import pdb
import pprint
import json

PACKAGE_BASE = os.path.abspath(
    os.path.split(
        os.path.dirname(__file__))[0])
print("PACKAGE_BASE: ", PACKAGE_BASE)
sys.path.append(PACKAGE_BASE)

from testconfig import config
from rdfframework.utilities import DictClass, pp, RdfNsManager, pp, \
                                   render_without_request, RdfConfigManager, \
                                   make_list
from rdfframework.rdfdatatypes import rdfdatatypes as rdt
from rdfframework.sparql import run_sparql_query
from rdfframework.framework import RdfFramework
print("CONFIG ---------------------------------------------------------------")
#config = DictClass(config)
pp.pprint(config)
print("----------------------------------------------------------------------")
CFG = RdfConfigManager(config=config)
NSM = RdfNsManager(config=CFG)
rdf_defs = CFG.RDF_DEFINITIONS

sparql = render_without_request("sparqlClassDefinitionList.rq",
                                 graph=CFG.RDF_DEFINITION_GRAPH,
                                 prefix=NSM.prefix())
print(sparql)
x = run_sparql_query(sparql, namespace=CFG.RDF_DEFINITIONS.namespace)
y = [rdt.pyrdf(i['kdsClass']) for i in x]

_sparql = render_without_request("sparqlClassDefinitionDataTemplate.rq",
                                 prefix=NSM.prefix(),
                                 item_uri="bf:Topic",
                                 graph=CFG.RDF_DEFINITION_GRAPH)
z = run_sparql_query(_sparql, namespace=rdf_defs.namespace)

def convert_query_row(row):
    """ Takes a JSON row and converts it to class """
    new_dict = {}
    for key, value in row.items():
        new_dict[key] = rdt.pyrdf(value)
    return DictClass(new_dict)

def convert_query_results(results):
    """ Takes a query result and converts it to a class """
    return [convert_query_row(row) for row in results]

v = convert_query_results(z)

def convert_to_class(con_results):
    new_dict = {}
    for row in con_results:
        #pdb.set_trace()

        if not new_dict.get(row.s):
            new_dict[row.s] = {}
        if not new_dict[row.s].get(row.p):
            new_dict[row.s][row.p] = row.o
        else:
            if not isinstance(new_dict[row.s][row.p], list):
                new_dict[row.s][row.p] = [new_dict[row.s][row.p]]
            new_dict[row.s][row.p].append(row.o)
    return DictClass(obj=new_dict, debug=False)

n = convert_to_class(v)
pyrdf = rdt.pyrdf

class RdfJsonEncoder(json.JSONEncoder):
    # def __init__(self, *args, **kwargs):
    #     if kwargs.get("uri_format"):
    #         self.uri_format = kwargs.pop("uri_format")
    #     else:
    #         self.uri_format = 'sparql_uri'
    #     super(RdfJsonEncoder, self).__init__(*args, **kwargs)

    def default(self, obj):
        # pdb.set_trace()
        if not hasattr(self, 'uri_format'):
            self.uri_format = 'sparql_uri'
        if isinstance(obj, RdfBaseClass):
            obj.uri_format = self.uri_format
            temp = obj.conv_json(self.uri_format)
            return temp
        elif isinstance(obj, RdfDataset):
            return obj._format()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

class RdfBaseClass(object):
    _reserved = ['add_property',
                 '_format',
                 '_reserved',
                 '_subject',
                 '_type',
                 'to_json',
                 'uri_format',
                 'conv_json']

    uri_format = 'sparql_uri'

    def __init__(self, sub):
        if sub.type:
            self._subject = DictClass({"s":sub, "p":None, "o":None})
        else:
            self._subject = sub
        if isinstance(sub, DictClass):
            # if sub.s == "rdf_type":
            #     pdb.set_trace()
            self.add_property(sub.p, sub.o)

    def add_property(self, pred, obj):
        if hasattr(self, pred):
            if isinstance(getattr(self, pred), list):
                new_list = getattr(self, pred)                
            else:
                new_list = [getattr(self, pred)]
            new_list.append(obj)
            setattr(self, pred, new_list)
        else:
            setattr(self, pred, obj)

    def __repr__(self):
        return pp.pformat(self._format())

    def _format(self, start=True):
        if not start:
            return None
        return_val = {}
        for attr in dir(self):
            if attr not in self._reserved and not attr.startswith("__"):
                return_val[attr] = getattr(self, attr)
        return return_val

    @property
    def to_json(self, start=True):
        return self.conv_json(self.uri_format)

    def conv_json(self, uri_format="sparql_uri"):

        def convert_item(ivalue):
            nvalue = ivalue
            if isinstance(ivalue, rdt.BaseRdfDataType):
                if ivalue.type == 'uri':
                    # pdb.set_trace()
                    nvalue = getattr(ivalue, uri_format)
                else:
                    nvalue = ivalue.to_json
            elif isinstance(ivalue, RdfBaseClass):
                if ivalue._subject.s.type == "uri":
                    # nvalue = value._subject.s.sparql_uri
                    # pdb.set_trace()
                    nvalue = getattr(value._subject.s, uri_format)
                elif ivalue._subject.s.type == "bnode":
                    nvalue = ivalue.conv_json(uri_format)
            elif isinstance(ivalue, list):
                nvalue = []
                for item in ivalue:
                    temp = convert_item(item)
                    nvalue.append(temp)
            return nvalue

        return_val = {}
        for attr in dir(self):
            if attr not in self._reserved and not attr.startswith("__"):
                value =  getattr(self, attr)
                return_val[attr] = convert_item(value)
        return return_val

class RdfDataset(object):
    """ A container for holding rdf data """
    _reserved = ['add_triple',
                  '_format',
                  '_reserved',
                  '_link_objects',
                  'load_data',
                  'class_types',
                  'subj_list',
                  'non_defined',
                  '',
                  ]

    def add_triple(self, sub, pred=None, obj=None, map={}, strip_orphans=False):
        """ Adds a triple to the dataset 

            args:
                sub: The subject of the triple or dictionary contaning a
                     triple
                pred: Optional if supplied in sub, predicate of the triple
                obj:  Optional if supplied in sub, object of the triple
                map: Optional, a ditionary mapping for a supplied dictionary
                strip_orphans: Optional, remove triples that have an orphan
                               blanknode as the object 
        """
        if isinstance(sub, DictClass) or isinstance(sub, dict):
            pred = sub[map.get('p','p')]
            obj = sub[map.get('o','o')]
            sub = sub[map.get('s','s')]

        pred = pyrdf(pred)
        obj = pyrdf(obj)
        sub = pyrdf(sub)

        # reference existing attr for bnodes and uris
        if obj.type in ['bnode']:
            if hasattr(self, obj):
                obj = getattr(self, obj)
            elif strip_orphans:
                return

        if hasattr(self, sub):
            getattr(self,sub).add_property(pred, obj)
        else:
            new_class = RdfBaseClass(sub)
            new_class.add_property(pred, obj)
            setattr(self, sub, new_class)
            print("new - %s %s %s" % (sub.sparql, pred.sparql, obj.sparql))

    def __repr__(self):
        return pp.pformat(self._format())    

    def _format(self, start=True):
        if not start:
            return None
        ignore_keys = self._reserved
        return_val = {}
        for attr in dir(self):
            if attr not in ignore_keys and not attr.startswith("_"):
                value = getattr(self, attr)
                if value._subject.s.type != 'bnode':
                    return_val[attr] = getattr(self, attr)
        return return_val

    def load_data(self, data, strip_orphans=False):
        """ Bulk adds rdf data to the class

            args:
                data: the data to be loaded
                strip_orphans: Optional, remove triples that have an orphan
                               blanknode as the object
        """
        if isinstance(data, list):
            data = self._convert_results(data)
        class_types = self._group_data(data)
        # generate classes and add attributes to the data
        self._generate_classes(class_types, self.non_defined)
        # add triples to the dataset
        for triple in data:
            self.add_triple(sub=triple, strip_orphans=strip_orphans)

    def _group_data(self, data):
        # strip all of the rdf_type triples and merge
        class_types = self._merge_classtypes(self._get_classtypes(data))
        self.subj_list = list([item.s for item in class_types])
        # get non defined classes
        self.non_defined = self._get_non_defined(data, class_types)
        return class_types

    @staticmethod
    def _get_classtypes(data):
        rtn_list = []
        remove_index = []
        for i, triple in enumerate(data):
            if triple.p == "rdf:type":
                remove_index.append(i)
                rtn_list.append(triple)
        for i in reversed(remove_index):
            data.pop(i)
        return rtn_list

    def _generate_classes(self, class_types, non_defined):
        for class_type in class_types:
            setattr(self, class_type.s, RdfBaseClass(class_type))
        for class_type in non_defined:
            setattr(self, class_type, RdfBaseClass(class_type))


    @staticmethod
    def _merge_classtypes(data):
        obj = {} 
        #pdb.set_trace()
        for i, triple in enumerate(data):
            if triple.s in obj.keys():
                #pdb.set_trace()
                obj[triple.s].o = make_list(obj[triple.s].o)
                #pdb.set_trace()
                obj[triple.s].o.append(triple.o)
                #pdb.set_trace()
            else:
                obj[triple.s] = triple
        return list(obj.values())

    @staticmethod
    def _get_non_defined(data, class_types):
        
        subj_set = set([item.s for item in class_types])
        print(subj_set)
        non_def_set = set([item.s for item in data])
        print(non_def_set)
        print(list(non_def_set - subj_set))
        return list(non_def_set - subj_set)

    @staticmethod    
    def _convert_results(data):
        converted_data = []
        converted_data = convert_query_results(data)
        return converted_data

ds = RdfDataset()
ds.load_data(z, True)
m = ds.rdf_type.to_json
RdfJsonEncoder.uri_format = "pyuri"
# print(json.dumps(x, indent=4))
print(json.dumps(ds, indent=4, cls=RdfJsonEncoder))
# for x in z:
#     ds.add_triple(x)
# ds._link_objects()
RdfFramework(reset=True)