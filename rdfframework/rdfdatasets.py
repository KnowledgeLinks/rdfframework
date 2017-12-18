"""    This module is used for setting an intial test configs and values for
the rdfframework """

import re
import json
import copy
import types
import datetime
import cssselect
import functools
import pprint, pdb
import rdflib

from cssselect.parser import parse as cssparse

from rdfframework import rdfclass
from rdfframework.utilities import DictClass, pp, make_list, UniqueList, cbool
from rdfframework.configuration import RdfConfigManager
from rdfframework.datatypes import pyrdf, BaseRdfDataType, Uri, BlankNode, \
        XsdString
from rdfframework.rdfclass import RdfClassBase, remove_parents, list_hierarchy
# import rdfframework.rdfclass as rdfclass
CFG = RdfConfigManager()


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

    __slots__ = ['classes',
                 'subj_list',
                 'non_defined',
                 'base_uri',
                 'base_class',
                 'relate_obj_types']

    def __init__(self, data=None, base_uri=None, **kwargs):
        start = datetime.datetime.now()
        if base_uri:
            base_uri = Uri(base_uri)
        self.base_uri = base_uri

        # realate_bnode_obj_types sets whether to relate the object of a class
        # back to itself

        self.relate_obj_types = ['bnode','uri']
        if kwargs.get("bnode_only"):
            self.relate_obj_types = ['bnode']

        if data:
            self.load_data(data, **kwargs)
            print("loaded %s triples in %s" % (len(data),
                                               (datetime.datetime.now()-start)))

    def __repr__(self):
        return "<Dataset([{'base_uri': '%s',\n'keys': '%s'}])>" % \
               (self.base_uri,
                [key.sparql for key in self.keys() if key.type != 'bnode'])

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

        # reference existing attr for bnodes and uris
        if obj.type in self.relate_obj_types :
            if strip_orphans and not self.get(obj):
                return
            obj = self.get(obj,obj)
        try:
            self[sub].add_property(pred, obj)
        except KeyError:
            self[sub] = RdfClassBase(sub, **kwargs)
            self[sub].add_property(pred, obj)

    def format(self, **kwargs):

        uri_format = kwargs.get('uri_format', "pyuri")
        output = kwargs.get('output', "dict")
        pretty = kwargs.get('pretty', False)
        remove = make_list(kwargs.get('remove', None))
        compress = kwargs.get('compress', False)
        sort = kwargs.get('sort', False)
        base_uri = kwargs.get("base_uri",None)
        add_ids = kwargs.get("add_ids", False)
        base_only = kwargs.get("base_only", False)

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

        conv_data = {key: value.conv_json(uri_format, add_ids)
                     for key, value in format_obj.items()
                     if value.subject.type not in remove}
        if base_only:
            try:
                conv_data = conv_data[self.base_uri]
            except KeyError:
                return "Base_uri undefined or not in dataset"

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
                          output='json',
                          add_ids=True))

    @property
    def view_main(self):
        """ prints the dataset in an easy to read format """
        print(self.format(remove='bnode',
                          sort=True,
                          pretty=True,
                          compress=True,
                          output='json',
                          base_only = True,
                          add_ids=True))

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
            data = self._convert_results(data, **kwargs)
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
                # if not isinstance(pred, Uri):
                #     pred = Uri(pred)
                if isinstance(obj, list):
                    for oo in obj:
                        if isinstance(oo, RdfClassBase):
                            oo = oo.subject
                        rtn_list.append((sub, pred, oo))
                else:
                    if isinstance(obj, RdfClassBase):
                        obj = obj.subject
                    rtn_list.append((sub, pred, obj))
        # rtn_list.sort(key=lambda tup: tup[0]+tup[1]+tup[2])
        if output:
            def size(value):
                if len(value) > 42:
                    value = "... %s" % value[-39:]
                spaces = 45 - len(value)
                return "%s%s" %(value," " * spaces)
            if output == "view":
                print("\n".join(
                        ["%s  %s%s%s" %
                         (i,
                          size(trip[0].sparql),
                          size(trip[1].sparql),
                          size(trip[2].sparql))
                         for i, trip in enumerate(rtn_list)]))
        else:
            return rtn_list

    @property
    def set_classes(self):
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
        self.classes = rtn_obj
        #return rtn_obj

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
        """ creates the class for each class in the data set

            args:
                class_types: list of class_types in the dataset
                non_defined: list of subjects that have no defined class
        """
        kwargs['dataset'] = self
        for class_type in class_types:
            self[class_type['s']] = self._get_rdfclass(class_type, **kwargs)\
                    (class_type, **kwargs)
            #setattr(self, class_type['s'], RdfBaseClass(class_type))
        for class_type in non_defined:
            self[class_type] = RdfClassBase(class_type, **kwargs)
            #setattr(self, class_type, RdfBaseClass(class_type))
        self.set_classes
        try:
            self.base_class = self[self.base_uri]
        except KeyError:
            self.base_class = None

    @staticmethod
    def _get_rdfclass(class_type, **kwargs):
        """ returns the instanticated class from the class list

            args:
                class_type: dictionary with rdf_types
        """
        def select_class(class_name):
            """ finds the class in the rdfclass Module"""
            try:
                return getattr(rdfclass, class_name.pyuri)
            except AttributeError:
                return RdfClassBase

        if kwargs.get("def_load"):
            return RdfClassBase

        if isinstance(class_type['o'], list):
            bases = [select_class(class_name) for class_name in class_type['o']]
            bases = [base for base in bases if base != RdfClassBase]
            if len(bases) == 0:
                return RdfClassBase
            elif len(bases) == 1:
                return bases[0]
            else:
                # return types.new_class("_".join(class_type['o']),
                #                        tuple(bases))
                bases = remove_parents(bases)
                if len(bases) == 1:
                    return bases[0]
                else:
                    new_class = type("_".join(class_type['o']),
                                     tuple(bases),
                                     {})
                    # new_class = types.new_class("_".join(class_type['o']),
                    #                             tuple(bases),
                    #                             {'multi_class': True})
                    new_class.hierarchy = list_hierarchy(class_type['o'][0],
                                                         bases)
                    new_class.class_names = [base.__name__ \
                            for base in bases \
                            if base not in [RdfClassBase, dict]]
                    return new_class
        else:
            return select_class(class_type['o'])

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
    def _convert_results(data, **kwargs):
        """ converts the results of a query to RdfDatatype instances

            args:
                data: a list of triples
        """
        if kwargs.get('debug'):
            for row in data:
                for key, value in row.items():
                    if value.get('value') =="2000-05-08T00:00:00.000Z":
                        pyrdf(value)
        return [{key:pyrdf(value) for key, value in row.items()}
                for row in data]

    def json_qry(self, qry_str, params):
        """ Takes a json query string and returns the results

        args:
            qry_str: query string
        """
        dallor_val = params.get("$")
        if isinstance(dallor_val, rdflib.URIRef):
            dallor_val = Uri(dallor_val)
        parsed_qry = parse_json_qry(qry_str)
        qry_parts = parsed_qry['qry_parts']
        post_actions = parsed_qry['params']
        # print(qry_parts)
        rtn_list = UniqueList()
        dataset = self
        if params.get('dataset'):
            dataset = params['dataset']
        for or_part in qry_parts:
            if or_part[1] == 0:
                if isinstance(dallor_val, dict):
                    result = dallor_val
                else:
                    try:
                        result = dataset[dallor_val]
                    except KeyError:
                        try:
                            result = dataset[Uri(dallor_val)]
                        except KeyError:
                            try:
                                result = dataset[BlankNode(dallor_val)]
                            except KeyError:
                                continue

                forward = True
                for part in or_part[0][1:]:
                    if part == "*":
                        forward = not forward
                    else:
                        if forward:
                            result = get_json_qry_item(result, part)
                        else:
                            result = get_reverse_json_qry_item(result,
                                                               part,
                                                               False)
            else:
                result = dataset
                parts = or_part[0].copy()
                parts.reverse()
                forward = False
                for part in parts[1:]:
                    if part == "*":
                        forward = not forward
                    else:
                        if forward:
                            result = get_json_qry_item(result, part)
                        else:
                            result = get_reverse_json_qry_item(result,
                                                               part,
                                                               False,
                                                               dallor_val)
            rtn_list += result
        for action in post_actions:
            rtn_list = action(rtn_list)
        return rtn_list


class ListLimiter(object):
    """ takes a list and a length limit and returns the list of appropriate
        length
    """
    def __init__(self, length):
        self.length = int(length)

    def __call__(self, action_list):
        if self.length >= 0:
            return action_list[:self.length]
        return action_list[self.length:]

class StripEnd(object):
    """ strips off the provided characters from the end of strings
    """
    def __init__(self, characters):
        self.regex = "[%s]+$" % characters

    def __call__(self, action_list):
        return [XsdString(re.sub(self.regex, '', str(action)))\
                for action in action_list]

class MakeDistinct(object):
    def __init__(self, active=True):
        self.active = cbool(active)

    def __call__(self, action_list):
        if not self.active:
            return action_list
        rtn_list = UniqueList()
        for action in action_list:
            rtn_list.append(action)
        return rtn_list

PARAM_LOOKUP = {"limit": ListLimiter,
                "stripend": StripEnd,
                "distinct": MakeDistinct}

@functools.lru_cache(maxsize=1000)
def parse_json_qry(qry_str):
    """ Parses a json query string into its parts

    args:
        qry_str: query string
        params: variables passed into the string
    """

    def param_analyzer(param_list):
        rtn_list = []
        for param in param_list:
            parts = param.strip().split("=")
            try:
                rtn_list.append(\
                        PARAM_LOOKUP[parts[0].strip().lower()](parts[1]))
            except IndexError:
                rtn_list.append(\
                        PARAM_LOOKUP[parts[0].strip().lower()]())
        return rtn_list

    def part_analyzer(part, idx):
        nonlocal dallor, asterick, question_mark
        if part == "$":
            dallor = idx
            return part
        elif part == "*":
            asterick = idx
            return part
        elif part == "?":
            question_mark = idx
            return part
        elif part.startswith("="):
            return part
        return cssparse(part)[0]
    # pdb.set_trace()
    main_parts = qry_str.split("|")
    or_parts = main_parts.pop(0).strip()
    params = param_analyzer(main_parts)
    rtn_list = []
    for or_part in [item.strip() for item in or_parts.split(",")]:
        dallor, asterick, question_mark = None, None, None
        dot_parts = or_part.split(".")
        rtn_list.append(([part_analyzer(part, i) \
                            for i, part in enumerate(dot_parts)],
                          dallor,
                          asterick,
                          question_mark))
    return {"qry_parts": rtn_list, "params": params}

def get_element(selector):
    """ searches for the element in a selector tree

    args:
        selector: the cssselect selector element

    returns:
        cssselect Element value
    """
    try:
        return selector.element
    except AttributeError:
        try:
            return get_element(selector.selector)
        except AttributeError:
            return None

def get_json_qry_item(dataset, param, no_key=False):
    """ reads the paramater and returns the selected element

    args:
        dataset: the dataset to search
        param: the paramater to search by
        no_key: wheather to use the 'param' 'element' to filter the list.
                This is passed True after the first run during recurssive call
                when the key has already been used to select subset of the
                dataset
    """

    def get_dataset_vals(ds, key, filter_tup=tuple()):
        def reduce_list(value):
            if isinstance(value, list):
                if len(value) == 1:
                    return value[0]
            return value

        def merge_list(value):
            if isinstance(value, list):
                rtn_list = []
                for item in value:
                    if isinstance(item, list):
                        rtn_list += item
                    else:
                        rtn_list.append(item)
                return list(set(rtn_list))
            return value

        def test_elem(elem, filter_tup):
            search_lst = elem
            if isinstance(elem, dict):
                search_lst = elem.get(filter_tup[0], [])
            if filter_tup[2] == '=':
                try:
                    if elem.subject == filter_tup[1]:
                        return True
                except AttributeError:
                    pass
                test_lst = [item for item in search_lst \
                            if (isinstance(item, dict) \
                                and item.subject == filter_tup[1]) \
                            or item == filter_tup[1]]
                if test_lst:
                    return True
                return False

        def filter_list(ds, key, filter_tup):
            rtn_list = ds
            if key:
                rtn_list = merge_list([reduce_list(reduce_list(elem)[key]) \
                                   for elem in ds if reduce_list(elem).get(key)])
            if filter_tup:
                return [elem for elem in rtn_list \
                        if test_elem(elem, filter_tup)]
            return rtn_list

        if isinstance(ds, list):
            return filter_list(ds, key, filter_tup)
        elif isinstance(ds, dict):
            search_dict = ds
            if key:
                search_dict = ds.get(key,[])
            if filter_tup:
                datalist = []
                for elem in search_dict:
                    if filter_tup[2] == "=":
                        # pdb.set_trace()
                        if filter_tup[1] in elem.get(filter_tup[0], []):
                            if isinstance(elem, list):
                                datalist += elem
                            else:
                                datalist.append(elem)
                    elif filter_tup[2] == "!=":
                        if filter_tup[1] not in elem.get(filter_tup[0], []):
                            datalist.append(elem)
                return datalist
                # return [elem for elem in ds[key] \
                #         if filter_tup[1] in elem.get(filter_tup[0], []) \
                #         and elem]
            return merge_list(search_dict)

    if param == "*":
        return dataset
    try:
        if param.startswith("="):
            # if the dataset length is '0' consider it a false match
            if dataset:
                return [pyrdf(param[1:])]
            return []
    except AttributeError:
        pass
    if hasattr(param, 'parsed_tree'):
        param = param.parsed_tree

    if hasattr(param, 'selector'):
        if no_key:
            key = None
        else:
            key = get_element(param.selector)
        rtn_obj = None
        if hasattr(param, 'ident'):
            if key:
                rtn_obj = get_dataset_vals(dataset,
                                           key,
                                           ('rdf_type',
                                            param.ident, "="))
            elif param.ident in dataset.get('rdf_type',[]):
                rtn_obj = dataset
            # pdb.set_trace()
        elif hasattr(param, 'attrib'):
            # if param.parsed_tree.attrib == 'bf_role':
            #     pdb.set_trace()
            rtn_obj = get_dataset_vals(dataset,
                                       key,
                                       (param.attrib,
                                        param.value,
                                        param.operator))
        if rtn_obj is not None:
            if hasattr(param, 'selector') \
                    and hasattr(param.selector, 'selector') \
                    and rtn_obj:
                rtn_obj = get_json_qry_item(rtn_obj, param.selector, True)
            return rtn_obj
        return dataset[key]
    elif hasattr(param, 'element'):
        key = param.element
        return get_dataset_vals(dataset, key)


def get_reverse_json_qry_item(dataset, param, no_key=False, initial_val=None):
    """ reads the paramater and returns the selected element

    args:
        dataset: the dataset to search
        param: the paramater to search by
        no_key: wheather to use the 'param' 'element' to filter the list.
                This is passed True after the first run during recurssive call
                when the key has already been used to select subset of the
                dataset
    """

    def get_dataset_vals(ds, key, filter_tup=tuple(), initial_val=None):
        def reduce_list(value):
            if isinstance(value, list):
                if len(value) == 1:
                    return value[0]
            return value

        def merge_list(value):
            if isinstance(value, list):
                rtn_list = []
                for item in value:
                    if isinstance(item, list):
                        rtn_list += item
                    else:
                        rtn_list.append(item)
                return list(set(rtn_list))
            return value

        def test_elem(elem, filter_tup):
            search_lst = elem
            if isinstance(elem, dict):
                search_lst = elem.get(filter_tup[0], [])
            if filter_tup[2] == '=':
                try:
                    if elem.subject == filter_tup[1]:
                        return True
                except AttributeError:
                    pass
                test_lst = [item for item in search_lst \
                            if (isinstance(item, dict) \
                                and item.subject == filter_tup[1]) \
                            or item == filter_tup[1]]
                if test_lst:
                    return True
                return False

        def filter_list(ds, key, filter_tup, initial_val=None):
            rtn_list = ds
            if key:
                rtn_list = merge_list([reduce_list(reduce_list(elem)[key]) \
                                   for elem in ds if reduce_list(elem).get(key)])
            if filter_tup:
                return [elem for elem in rtn_list \
                        if test_elem(elem, filter_tup)]
            return rtn_list

        def reverse_filter_list(ds, key, filter_tup, initial_val=None):

            def get_reverse_ds_dict(ds, key, filter_tup, initial_val=None):
                data_list = UniqueList()
                if not key and not initial_val:
                    return data_list
                for sub, ds_rdf_class in ds.items():
                    for pred, obj in ds_rdf_class.items():
                        if key and pred == key:
                            if initial_val:
                                if initial_val in obj:
                                    data_list.append(ds_rdf_class)
                            else:
                                data_list.append(ds_rdf_class)
                        if not key and initial_val:
                            if initial_val in obj:
                                data_list.append(ds_rdf_class)
                # pdb.set_trace()
                return data_list

            if isinstance(ds, dict):
                return get_reverse_ds_dict(ds, key, filter_tup, initial_val)
            elif isinstance(ds, list):
                rtn_list = UniqueList()
                for item in ds:
                    rtn_list += get_reverse_ds_dict(ds,
                                                    key,
                                                    filter_tup,
                                                    initial_val)
                return rtn_list


        if isinstance(ds, list):
            return reverse_filter_list(ds, key, filter_tup, initial_val)
        elif isinstance(ds, dict):
            search_dict = ds
            if key:
                search_dict = reverse_filter_list(ds,
                                                  key,
                                                  filter_tup,
                                                  initial_val)
            # pdb.set_trace()
            if filter_tup:
                datalist = []
                for elem in search_dict:
                    if filter_tup[2] == "=":
                        # pdb.set_trace()
                        if filter_tup[1] in elem.get(filter_tup[0], []):
                            if isinstance(elem, list):
                                datalist += elem
                            else:
                                datalist.append(elem)
                    elif filter_tup[2] == "!=":
                        if filter_tup[1] not in elem.get(filter_tup[0], []):
                            datalist.append(elem)
                return datalist
            return merge_list(search_dict)



    if param == "*":
        pass
    # pdb.set_trace()
    if hasattr(param, 'parsed_tree'):
        param = param.parsed_tree

    if hasattr(param, 'selector'):

        if no_key:
            key = None
        else:
            key = get_element(param.selector)
        rtn_obj = None
        if hasattr(param, 'ident'):
            rtn_obj = get_dataset_vals(dataset,
                                       key,
                                       ('rdf_type',
                                        param.ident, "="))
        elif hasattr(param, 'attrib'):
            # if param.parsed_tree.attrib == 'bf_role':
            #     pdb.set_trace()
            rtn_obj = get_dataset_vals(dataset,
                                       key,
                                       (param.attrib,
                                        param.value,
                                        param.operator))
        if rtn_obj is not None:
            if hasattr(param, 'selector') \
                    and hasattr(param.selector, 'selector') \
                    and rtn_obj:
                rtn_obj = get_json_qry_item(rtn_obj, param.selector, True)
            return rtn_obj
        return dataset.get(key, [])
    elif hasattr(param, 'element'):
        key = param.element
        return get_dataset_vals(dataset, key, initial_val=initial_val)

def override_ascii_lower(string):
    """do not use lowercase in cssselect"""
    return string.encode('utf8').decode('utf8')

cssselect.parser.ascii_lower = override_ascii_lower
