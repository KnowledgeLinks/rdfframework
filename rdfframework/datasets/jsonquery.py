""" This module parses and processes a json query for use with a RDF dataset """

import cssselect
import functools
import rdflib
import pdb

from cssselect.parser import parse as cssparse
from rdfframework.datatypes import Uri, pyrdf, BlankNode
from rdfframework.utilities import UniqueList
from .qryprocessors import JsonQryProcessor

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
                        JsonQryProcessor[parts[0].strip().lower()](parts[1]))
            except IndexError:
                rtn_list.append(\
                        JsonQryProcessor[parts[0].strip().lower()]())
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
    for or_part in [item.strip()
                    for item in or_parts.split(",")
                    if item.strip()]:
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
                try:
                    return list(set(rtn_list))
                except TypeError:
                    return rtn_list
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
                                   for elem in ds
                                   if isinstance(reduce_list(elem), dict)
                                   and reduce_list(elem).get(key)])
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
            elif param.ident in dataset.get('rdf_type', []):
                rtn_obj = dataset
            else:
                rtn_obj = [value for value in dataset.values()
                           if param.ident in value.get('rdf_type', [])]
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
        if key:
            return dataset[key]
        else:
            return dataset
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
                if hasattr(ds, 'rmap') and initial_val:
                    # pdb.set_trace()
                    if key:
                        try:
                            return ds.rmap[initial_val][key]
                        except KeyError:
                            return []
                    else:
                        return ds.rmap[initial_val]
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

def json_qry(dataset, qry_str, params={}):
    """ Takes a json query string and returns the results

    args:
        dataset: RdfDataset to query against
        qry_str: query string
        params: dictionary of params
    """
    # if qry_str.startswith("$.bf_itemOf[rdf_type=bf_Print].='print',\n"):
    #     pdb.set_trace()
    if not '$' in qry_str:
        qry_str = ".".join(['$', qry_str.strip()])
    dallor_val = params.get("$", dataset)
    if isinstance(dallor_val, rdflib.URIRef):
        dallor_val = Uri(dallor_val)
    if qry_str.strip() == '$':
        return [dallor_val]
    parsed_qry = parse_json_qry(qry_str)
    qry_parts = parsed_qry['qry_parts']
    post_actions = parsed_qry['params']
    # print(qry_parts)
    rtn_list = UniqueList()
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

