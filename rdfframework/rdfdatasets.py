"""    This module is used for setting an intial test configs and values for 
the rdfframework """

import pdb
import json
import copy

from rdfframework.utilities import DictClass, pp, make_list
from rdfframework.rdfdatatypes import pyrdf, BaseRdfDataType
from rdfframework.rdfclass import RdfBaseClass


class RdfJsonEncoder(json.JSONEncoder):
    # def __init__(self, *args, **kwargs):
    #     if kwargs.get("uri_format"):
    #         self.uri_format = kwargs.pop("uri_format")
    #     else:
    #         self.uri_format = 'sparql_uri'
    #     super(RdfJsonEncoder, self).__init__(*args, **kwargs)
    uri_format = 'sparql_uri'

    def default(self, obj):
        pdb.set_trace()
        if isinstance(obj, RdfBaseClass):
            pdb.set_trace()
            obj.uri_format = self.uri_format
            temp = obj.conv_json(self.uri_format)
            return temp
        elif isinstance(obj, RdfDataset):
            pdb.set_trace()
            return obj._format(self.uri_format)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class RdfDataset(dict):
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

    def add_triple(self, sub, pred=None,  obj=None, **kwargs):
        """ Adds a triple to the dataset 

            args:
                sub: The subject of the triple or dictionary contaning a
                     triple
                pred: Optional if supplied in sub, predicate of the triple
                obj:  Optional if supplied in sub, object of the triple

            kwargs:
                map: Optional, a ditionary mapping for a supplied dictionary
                strip_orphans: Optional, remove triples that have an orphan
                               blanknode as the object 
                obj_method: if "list" than the object will be returned in the
                            form of a list
        """
        map = kwargs.get('map',{})
        strip_orphans = kwargs.get("strip_orphans", False)
        obj_method = kwargs.get("obj_method")
        if isinstance(sub, DictClass) or isinstance(sub, dict):
            pred = sub[map.get('p','p')]
            obj = sub[map.get('o','o')]
            sub = sub[map.get('s','s')]

        pred = pyrdf(pred)
        obj = pyrdf(obj)
        sub = pyrdf(sub)

        # reference existing attr for bnodes
        if obj.type in ['bnode']:
            if strip_orphans and not self.get(obj):
                return
            obj = self.get(obj,obj)

        try:
            self[sub].add_property(pred, obj, obj_method)
        except KeyError:
            self[sub] = RdfBaseClass(sub, **kwargs)
            self[sub].add_property(pred, obj, obj_method)

    def format(self, **kwargs):

        uri_format = kwargs.get('uri_format', "pyuri")
        output = kwargs.get('output', "dict")
        pretty = kwargs.get('pretty', False)
        remove = make_list(kwargs.get('remove', None))
        compress = kwargs.get('compress', False)
        sort = kwargs.get('sort', False)

        if compress:
            new_obj = copy.deepcopy(self)
            for key, value in new_obj.items():
                for skey, svalue in value.items():
                    if isinstance(svalue, list) and len(svalue) == 1:
                        new_obj[key][skey] = svalue[0]
            format_obj = new_obj
        else:
            format_obj = self
        if remove:
            remove = make_list(remove)

        conv_data = {key: value.conv_json(uri_format)
                     for key, value in format_obj.items()
                     if value._subject['s'].type not in remove}
        if output.lower() == 'json':
            indent = None
            if pretty:
                indent = 4
            return json.dumps(conv_data, indent=indent, sort_keys=sort)
        elif output.lower() == 'dict':
            return conv_data

    @property
    def view(self):
        """ prints the dataset in an easy to read format """
        print(self.format(remove='bnode', 
                          sort=True,
                          pretty=True,
                          compress=True,
                          output='json'))


    def load_data(self, data, **kwargs):
        """ Bulk adds rdf data to the class

            args:
                data: the data to be loaded

            kwargs:
                strip_orphans: True or False - remove triples that have an
                               orphan blanknode as the object
                obj_method: "list", or None: if "list" the object of a method 
                            will be in the form of a list.
        """
        if isinstance(data, list):
            data = self._convert_results(data)
        class_types = self._group_data(data)
        # generate classes and add attributes to the data
        self._generate_classes(class_types, self.non_defined, **kwargs)
        # add triples to the dataset
        for triple in data:
            self.add_triple(sub=triple, **kwargs)

    def _group_data(self, data):
        """ processes the data in to groups prior to loading into the 
            dataset

            args:
                data: a list of triples
        """
        # strip all of the rdf_type triples and merge
        class_types = self._merge_classtypes(self._get_classtypes(data))
        self.subj_list = list([item['s'] for item in class_types])
        # get non defined classes
        self.non_defined = self._get_non_defined(data, class_types)
        return class_types

    def triples(self, output=None):
        rtn_list = []
        for sub, props in self.items():
            for pred, obj in props.items():
                if isinstance(obj, list):
                    for oo in obj:
                        if isinstance(oo, RdfBaseClass):
                            oo = oo._subject['s']
                        rtn_list.append((sub, pred, oo))
                else:
                    if isinstance(obj, RdfBaseClass):
                        obj = obj._subject['s']
                    rtn_list.append((sub, pred, obj))
        rtn_list.sort(key=lambda tup: tup[0]+tup[1]+tup[2])
        if output:
            def size(value):
                spaces = 25 - len(value)
                return "%s%s" %(value," " * spaces)
            if output == "view":
                print("\n".join(
                        ["%s  %s%s%s" % 
                         (i, size(trip[0].sparql), size(trip[1].sparql), trip[2].sparql) 
                         for i, trip in enumerate(rtn_list)]))
        else:        
            return rtn_list

    @property
    def classes(self):
        def add_class(key, value):
            nonlocal rtn_obj
            try:
                #pdb.set_trace()
                rtn_obj[value].append(key)
            except AttributeError:
                #pdb.set_trace()
                rtn_obj[value] = [rtn_obj[value['rdf_type']]]
                rtn_obj[value].append(key)
            except KeyError:
                #pdb.set_trace()
                rtn_obj[value] = [key]
            except TypeError:
                #pdb.set_trace()
                for item in value:
                    add_class(key, item)
        rtn_obj = {}
        for key, value in self.items():
            #pdb.set_trace()
            try:
                add_class(key, value['rdf_type'])
            except KeyError:
                pass

        return rtn_obj

    @property
    def classes2(self):
        rtn_obj = {}
        for t in self.triples():
            if t[1] == 'rdf_type':
                try:
                    rtn_obj[t[2]].append(t[0])
                except KeyError:
                    rtn_obj[t[2]] = [t[0]]

        return rtn_obj

    @property
    def classes3(self):
        rtn_obj = {}
        expand = [[(i,key) for i in value['rdf_type']] 
                  for key, value in self.items() if value.get('rdf_type')]
        for item in expand:
            rtn_obj[item[0][0]] = []
        for item in expand:
            rtn_obj[item[0][0]].append(item[0][1])

        return rtn_obj
        
    @staticmethod
    def _get_classtypes(data):
        """ returns all of the triples where rdf:type is the predicate and 
            removes them from the data list

            agrs:
                data: a list of triples
        """ 
        rtn_list = []
        remove_index = []
        for i, triple in enumerate(data):
            if triple['p'] == "rdf:type":
                remove_index.append(i)
                rtn_list.append(triple)
        for i in reversed(remove_index):
            data.pop(i)
        return rtn_list

    def _generate_classes(self, class_types, non_defined, **kwargs):
        for class_type in class_types:
            self[class_type['s']] = RdfBaseClass(class_type, **kwargs)
            #setattr(self, class_type['s'], RdfBaseClass(class_type))
        for class_type in non_defined:
            self[class_type] = RdfBaseClass(class_type, **kwargs)
            #setattr(self, class_type, RdfBaseClass(class_type))


    @staticmethod
    def _merge_classtypes(data):
        obj = {} 
        for triple in data:
            try:
                obj[triple['s']]['o'].append(triple['o'])
            except AttributeError:
                obj[triple['s']]['o'] = [obj[triple['s']]['o']]
                obj[triple['s']]['o'].append(triple['o'])
            except KeyError:
                obj[triple['s']] = triple
        return list(obj.values())

    @staticmethod
    def _get_non_defined(data, class_types):
        """ returns a list of URIs and blanknodes that are not defined within
            the dataset. For example: schema:Person has an associated rdf:type 
            then it is considered defined. 

            args:
                data: a list of triples
                class_types: list of subjects that are defined in the dataset
        """
        subj_set = set([item['s'] for item in class_types])
        non_def_set = set([item['s'] for item in data])
        return list(non_def_set - subj_set)

    @staticmethod    
    def _convert_results(data):
        """ converts the results of a query to RdfDatatype instances

            args:
                data: a list of triples
        """ 
        return [{key:pyrdf(value) for key, value in row.items()} 
                for row in data]