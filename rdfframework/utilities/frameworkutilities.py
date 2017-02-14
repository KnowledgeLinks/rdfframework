"""frameworkutilities.py

Module of helper functions used in the RDF Framework.

"""
__author__ = "Mike Stabile, Jeremy Nelson"

import copy
import pdb
import logging
import inspect

from types import ModuleType
from flask import current_app, json
from .uriconvertor import iri, clean_iri, uri, pyuri, convert_obj_to_rdf_namespace
from hashlib import sha1
from .debug import pp
from rdfframework.getframework import fw_config
import rdfframework.rdfdatatypes as dt
try:    
    pass
except:
    print("************* IMPORT ERROR -rdf_format")
    pass

try:
    print(dt.rdf_format(123))
    print("$$$$$$$$$$$$$$$$$$$ MONEY")
except:
    print("&&&&&&&&&&&&&&&&&&& NOPE")

MNAME = inspect.stack()[0][1]

# DC = Namespace("http://purl.org/dc/elements/1.1/")
# DCTERMS = Namespace("http://purl.org/dc/terms/")
# DOAP = Namespace("http://usefulinc.com/ns/doap#")
# FOAF = Namespace("http://xmlns.com/foaf/spec/")
# SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
DEBUG = True

def uid_to_repo_uri(id_value):
    if id_value:
        _uri = "{}/{}/{}/{}/{}/{}".format(fw_config().get('REPOSITORY_URL'),
                                          id_value[:2],
                                          id_value[2:4],
                                          id_value[4:6],
                                          id_value[6:8],
                                          id_value)
        return _uri

def convert_spo_to_dict(data, mode="subject", option="string", method="t-store"):
    '''Takes the SPAQRL query results and converts them to a python Dict

    mode: subject --> groups based on subject
    '''
    try:
        from rdfframework.datatypes import rdf_format
    except:
        pass

    try:
        print(rdf_format(123))
        print("$$$$$$$$$$$$$$$$$$$ MONEY")
    except:
        print("&&&&&&&&&&&&&&&&&&& NOPE")
    def get_o(item, method, option):
        if method == "t-store":
            return xsd_to_python(item['o']['value'], item['o'].get(\
                                "datatype"), item['o']['type'], option)
            #return rdf_format(item['o'])
        elif method == "rdflib":
            return str(item[len(item)-1])

    #pdb.set_trace()
    if data is None:
        return None
    _return_obj = {}
    _list_obj = False
    if method != 'rdflib':
        method = "t-store"
    if mode == "subject":
        for item in data:
            # determine data is list of objects
            if method == "t-store":
                _sv = item['s']['value']
                _pv = item['p']['value']
                item_id = item.get('itemID',{}).get('value',None)
            elif method == "rdflib":
                if len(item) > 3:
                    item_id = item[0]
                    _sv = str(item[1])
                    _pv = str(item[2])
                else:
                    item_id = None
                    _sv = str(item[0])
                    _pv = str(item[1])

            if item_id:
                _list_obj = True
                _iv = item_id
                if _return_obj.get(_iv):
                    if _return_obj[_iv].get(_sv):
                        if _return_obj[_iv][_sv].get(_pv):
                            _obj_list = make_list(\
                                    _return_obj[_iv][_sv][_pv])
                            _obj_list.append(get_o(item, method, option))
                            # _obj_list.append(\
                            #         xsd_to_python(item['o']['value'], \
                            #         item['o'].get("datatype"), \
                            #         item['o']['type'],
                            #         option))
                            _return_obj[_iv][_sv][_pv] = _obj_list
                        else:
                            _return_obj[_iv][_sv][_pv] = get_o(item, 
                                                               method,
                                                               option)
                    else:
                        _return_obj[_iv][_sv] = {}
                        _return_obj[_iv][_sv][_pv] = get_o(item, method, option)
                else:
                    _return_obj[_iv] = {}
                    _return_obj[_iv][_sv] = {}
                    _return_obj[_iv][_sv][_pv] = get_o(item, method, option)

            # if not a list of objects
            else:
                if _return_obj.get(_sv):
                    if _return_obj[_sv].get(_pv):
                        _obj_list = make_list(\
                                _return_obj[_sv][_pv])
                        _obj_list.append(get_o(item, method, option))
                        _return_obj[_sv][_pv] = _obj_list
                    else:
                        _return_obj[_sv][_pv] = get_o(item, method, option)
                else:
                    _return_obj[_sv] = {}
                    _return_obj[_sv][_pv] = get_o(item, method, option)
        if _list_obj:
            _return_list = []
            for _key, _value in _return_obj.items():
                _value[_key]["subjectUri"] = _key
                _return_list.append(_value)
            return _return_list
        else:
            return _return_obj

def convert_spo_nested(data, base_id, hash_ids=True):
    """ Reads throught the data converts to a nested data object 

    args:
        data: The s p o query results to convert
        base_id: the base subject_uri
        hash_ids: [True, False] hashes the id's 
    """
    base_id = uri(base_id)
    converted_data = convert_spo_to_dict(data)
    rtn_obj = converted_data.pop(clean_iri(base_id))
    if hash_ids:
        rtn_obj['uri'] = iri(base_id)
        base_id = sha1(iri(base_id).encode()).hexdigest()
    rtn_obj["id"] = base_id
    #pdb.set_trace()
    for key, value in converted_data.items():
        new_val = value
        if not re.match(r'^t\d+', key):
            new_val['uri'] = iri(key)
            new_val['id'] = sha1(key.encode()).hexdigest()
        #pdb.set_trace()
        for r_key, r_value in rtn_obj.items():
            #pdb.set_trace()
            if isinstance(r_value, list):
                for i, item in enumerate(r_value):
                    if not isinstance(item, dict) and iri(item) == iri(key):
                        r_value[i] = new_val
            elif isinstance(r_value, dict):
                pass
            else:
                if iri(r_value) == iri(key):
                    rtn_obj[r_key] = new_val
    return rtn_obj

def convert_spo_def(data, base_id, hash_ids=True):
    """ Reads throught the data converts to an application definition object 

    args:
        data: The s p o query results to convert
        base_id: the base subject_uri
        hash_ids: [True, False] hashes the id's 
    """
    base_id = uri(base_id)
    converted_data = convert_spo_to_dict(data)
    rtn_obj = {}
    rtn_obj[iri(base_id)] = converted_data.pop(clean_iri(base_id))
    if rtn_obj[iri(base_id)].get("rdfs_subClassOf"):
        parent_class = rtn_obj[iri(base_id)].get("rdfs_subClassOf")
        parent_data = converted_data.pop(clean_iri(parent_class))
    blanknodes = {}
    temp_data = copy.deepcopy(converted_data)
    for key, val in temp_data.items():
        if re.match(r'^t\d+', key):
            blanknodes[key] = converted_data.pop(key)
    clean_nodes = bnode_nester(blanknodes, copy.deepcopy(blanknodes))
    properties = bnode_nester(converted_data, clean_nodes)
    rtn_obj[iri(base_id)]['kds_properties'] = properties
    return rtn_obj

def bnode_nester(obj, bnodes):
    ''' takes a dictionary object and a list of blanknodes and nests them where
    the key is

    all keys that match the pattern. 
    
    args:
        obj: dictionay object to search trhough
        bnodes: dictionay of blanknodes'''
    
    if isinstance(obj, list):
        return_list = []
        for item in obj:
            if isinstance(item, list):
                return_list.append(bnode_nester(item, bnodes))
            elif isinstance(item, set):
                return_list.append(list(item))
            elif isinstance(item, dict):
                return_list.append(bnode_nester(item, bnodes))
            elif isinstance(item, str) \
                    and re.match(r'^t\d+', item) \
                    and bnodes.get(item):
                return_list.append(bnodes.get(item))
            else:
                try:
                    json.dumps(item)
                    return_list.append(item)
                except:
                    return_list.append(str(type(item)))
        return return_list
    elif isinstance(obj, set):
        return bnode_nester(list(item), bnodes)
    elif isinstance(obj, dict):
        return_obj = {}
        for key, item in obj.items():
            if isinstance(item, list):
                return_obj[key] = bnode_nester(item, bnodes)
            elif isinstance(item, set):
                return_obj[key] = list(item)
            elif isinstance(item, dict):
                return_obj[key] = bnode_nester(item, bnodes)
            elif isinstance(item, str) \
                    and re.match(r'^t\d+', item) \
                    and bnodes.get(item):
                return_obj[key] = bnodes.get(item)
            else:
                try:
                    json.dumps(item)
                    return_obj[key] = item
                except:
                    return_obj[key] = str(type(item))
        return return_obj
    elif isinstance(item, str) \
            and re.match(r'^t\d+', item) \
            and bnodes.get(item):
        return bnodes.get(item)
    else:
        try:
            json.dumps(obj)
            return obj
        except:
            return str(type(obj))

def get_app_ns_uri(value):
    ''' looks in the framework for the namespace uri'''
    for _ns in get_framework().rdf_app_dict['application'].get(\
                                                       "appNameSpace", []):
        if _ns.get('prefix') == value:
            return _ns.get('nameSpaceUri')


class DataStatus(object):
    """ Checks and updates the data status from the triplestore 
        
    args:
        group: the datagroup for statuses
    """
    ln = "%s-DataStatus" % MNAME
    log_level = logging.DEBUG


    def __init__(self, group, **kwargs):

        self.group = group

    def get(self, status_item):
        """ queries the database and returns that status of the item.

        args:
            status_item: the name of the item to check
        """
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        from rdfframework.sparql import run_sparql_query
        sparql = '''
            SELECT ?loaded
            WHERE {{
                kdr:{0} kds:{1} ?loaded .
            }}'''
        value = run_sparql_query(sparql=sparql.format(self.group, status_item))
        if len(value) > 0 and cbool(value[0].get('loaded',{}).get("value",False)):
            return True
        else:
            return False

    def set(self, status_item, status):
        """ sets the status item to the passed in paramaters

        args:
            status_item: the name if the item to set
            status: boolean value to set the item
        """
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        from rdfframework.sparql import run_sparql_query
        sparql = '''
            DELETE {{
                kdr:{0} kds:{1} ?o
            }}
            INSERT {{
                kdr:{0} kds:{1} "{2}"^^xsd:boolean
            }} 
            WHERE {{
                OPTIONAL {{ kdr:{0} kds:{1} ?o }}
            }}'''
        return run_sparql_query(sparql=sparql.format(self.group, 
                                                     status_item,
                                                     str(status).lower()),
                                mode='update')

def convert_ispo_to_dict(data, mode="subject", base=None):
    '''Takes the SPAQRL query results and converts them to a python Dict

    Args:
        data: the list of items
        mode: subject --> groups based on subject
        base: the base class for the  subClassOf inheritance

    '''
    if data is None:
        return None
    rtn_obj = {}
    base = uri(clean_iri(base))
    _list_obj = False
    dbl_bn_list = []
    sgl_bn_list = []
    no_bn_list = []
    new_data = []
    for item in data:
        if item['s']['type'] == "bnode" and item['o']['type'] == "bnode":
            dbl_bn_list.append(item)
        elif item['s']['type'] == "bnode":
            sgl_bn_list.append(item)
        else:
            no_bn_list.append(item)
    singles = convert_spo_to_dict(sgl_bn_list)
    for item in dbl_bn_list:
        item['o']['value'] = dict.copy(singles.get(item['o']['value'],{}))
    doubles = convert_spo_to_dict(dbl_bn_list)
    for key, value in doubles.items():
        if singles.get(key):
            for bn_key, bn_val in value.items():
                if bn_key in singles[key].keys():
                    if isinstance(singles[key][bn_key], list) and \
                            bn_val not in singles[key][bn_key]:
                        singles[key][bn_key].append(bn.val)
                    elif bn_val != singles[key][bn_key]:
                        singles[key][bn_key] = [singles[key][bn_key], bn_val]
                else:
                    singles[key][bn_key] = bn_val
        else:
            singles['key'] = value
    subclass_list = []
    subclass_uri = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
    for item in no_bn_list:
        if item['o']['type'] == "bnode":
            item['o']['value'] = singles.get(item['o']['value'])
        if item['p']['value'] == subclass_uri:
            subclass_list.append(item)
    # find the subClassOf order
    ordered_subclasses = []
    
    if base:
        # group the query based on class
        grouped_by_class =  {}
        for item in no_bn_list:
            if grouped_by_class.get(item['item']['value']):
                grouped_by_class[item['item']['value']].append(item)
            else:
                grouped_by_class[item['item']['value']]= [item]
        # convert each group to a dict
        for key, value in grouped_by_class.items():
            grouped_by_class[key]=convert_spo_def(value, key)[iri(key)]
        # determine the subclass order
        current_class = base
        finished = False
        while not finished:
            found = False
            for item in subclass_list:
                if item['s']['value'] == current_class:
                    ordered_subclasses.append(current_class)
                    current_class = item['o']['value'];
                    found = True
                    break
            if not found:
                finished = True
                ordered_subclasses.append(current_class)
        # write each class to a final dict where the subclass overides any
        # parent properties
        rtn_obj = {}
        first = IsFirst()
        for subclass in reversed(ordered_subclasses):
            if first.first():
                rtn_obj = grouped_by_class[subclass]
            else:

                for key, value in grouped_by_class[subclass].items():
                    if key == "kds_properties":
                        if rtn_obj.get(key):
                            for prop, data in value.items():
                                rtn_obj[key][prop] = data
                        else:
                            rtn_obj[key] = value
                    else:
                        rtn_obj[key] = value
    return rtn_obj


