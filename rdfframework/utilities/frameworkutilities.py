"""frameworkutilities.py

Module of helper functions used in the RDF Framework.

"""
__author__ = "Mike Stabile, Jeremy Nelson"

import copy
import datetime
import os
import re
import requests
import pdb
import logging
import inspect

from types import ModuleType
from base64 import b64encode, b64decode
from flask import current_app, json
from jinja2 import Template, Environment, FileSystemLoader
from rdflib import Namespace, XSD
from dateutil.parser import parse
from .uriconvertor import iri, clean_iri, uri, pyuri, convert_obj_to_rdf_namespace
from hashlib import sha1

MNAME = inspect.stack()[0][1]

# DC = Namespace("http://purl.org/dc/elements/1.1/")
# DCTERMS = Namespace("http://purl.org/dc/terms/")
# DOAP = Namespace("http://usefulinc.com/ns/doap#")
# FOAF = Namespace("http://xmlns.com/foaf/spec/")
# SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
DEBUG = True

FRAMEWORK_BASE = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
# if not os.path.exists(FRAMEWORK_BASE):
#     #! Quick hack to get running on Docker container -- jpn 2016-03-08
#     FRAMEWORK_BASE = "/opt/intro2libsys/ebadges/rdfframework/rdfframework"
JSON_LOCATION = os.path.join(FRAMEWORK_BASE, "json-definitions")

ENV = Environment(loader=FileSystemLoader(
    [os.path.join(FRAMEWORK_BASE, "sparql", "queries"),
     os.path.join(FRAMEWORK_BASE, "turtle")]))

def nz(value, none_value, strict=True):
    ''' This function is named after an old VBA function. It returns a default
        value if the passed in value is None. If strict is False it will
        treat an empty string as None as well.

        example:
        x = None
        nz(x,"hello")
        --> "hello"
        nz(x,"")
        --> ""
        y = ""
        nz(y,"hello")
        --> ""
        nz(y,"hello", False)
        --> "hello" '''
    if not DEBUG:
        debug = False
    else:
        debug = False
    if debug: print("START nz frameworkutilities.py ----------------------\n")
    if value is None and strict:
        return_val = none_value
    elif strict and value is not None:
        return_val = value
    elif not strict and not is_not_null(value):
        return_val = none_value
    else:
        return_val = value
    if debug: print("value: %s | none_value: %s | return_val: %s" %
        (value, none_value, return_val))
    if debug: print("END nz frameworkutilities.py ----------------------\n")
    return return_val

def render_without_request(template_name, template_path=None, **template_vars):
    """
    Usage is the same as flask.render_template:

    render_without_request('my_template.html', var1='foo', var2='bar')
    """
    if template_path:
        env = Environment(loader=FileSystemLoader([os.path.join(template_path)]))
    else:
        env = ENV
    template = env.get_template(template_name)
    return template.render(**template_vars)


def cbool(value, strict=True):
    ''' converts a value to true or false. Python's default bool() function
    does not handle 'true' of 'false' strings '''
    return_val = value
    if is_not_null(value):
        if isinstance(value, bool):
            return_val = value
        elif isinstance(value, str):
            if value.lower() in ['true', '1', 't', 'y', 'yes']:
                return_val = True
            elif value.lower() in ['false', '0', 'n', 'no']:
                return_val = False
            else:
                if strict:
                    return_val = None
    else:
        if strict:
            return_val = None
    return return_val


def is_not_null(value):
    ''' test for None and empty string '''
    return value is not None and len(str(value)) > 0

def is_valid_object(uri_string):
    '''Test to see if the string is a object store'''
    uri_string = uri_string
    return True

def make_list(value):
    ''' Takes a value and turns it into a list if it is not one

    !!!!! This is important becouse list(value) if perfomed on an
    dictionary will return the keys of the dictionary in a list and not
    the dictionay as an element in the list. i.e.
        x = {"first":1, "second":2}
        list(x) = ["first", "second"]
        or use this [x,]
        make_list(x) =[{"first":1, "second":2}]
    '''
    if not isinstance(value, list):
        value = [value]
    return value

def make_set(value):
    ''' Takes a value and turns it into a set

    !!!! This is important because set(string) will parse a string to
    individual characters vs. adding the string as an element of
    the set i.e.
        x = 'setvalue'
        set(x) = {'t', 'a', 'e', 'v', 'u', 's', 'l'}
        make_set(x) = {'setvalue'}
        or use set([x,]) by adding string as first item in list.
    '''
    if isinstance(value, list):
        value = set(value)
    elif not isinstance(value, set):
        value = set([value,]) 
    return value

def uid_to_repo_uri(id_value):
    if id_value:
        _uri = "{}/{}/{}/{}/{}/{}".format(fw_config().get('REPOSITORY_URL'),
                                          id_value[:2],
                                          id_value[2:4],
                                          id_value[4:6],
                                          id_value[6:8],
                                          id_value)
        return _uri

def make_triple(sub, pred, obj):
    """Takes a subject predicate and object and joins them with a space
	in between

    Args:
        sub -- Subject
        pred -- Predicate
        obj  -- Object
    Returns
        str
	"""
    return "{s} {p} {o} .".format(s=sub, p=pred, o=obj)

def xsd_to_python(value, data_type, rdf_type="literal", output="python"):
    ''' This will take a value and xsd data_type and convert it to a python
        variable'''
    from rdfframework import get_framework as rdfw
    if data_type:
        data_type = data_type.replace(str(XSD), "")
    if not value or isinstance(value, dict) or isinstance(value, list):
        return value
    elif rdf_type == "uri":
        return iri(value)
    elif not is_not_null(value):
        return value
    elif data_type == "xsd_anyURI":
        # URI (Uniform Resource Identifier)
        return value
    elif data_type == "xsd_base64Binary":
        # Binary content coded as "base64"
        return b64decode(value)
    elif data_type == "xsd_boolean":
        # Boolean (true or false)
        if output == "string":
            return str(value).lower()
        else:
            return cbool(value)
    elif data_type == "xsd_byte":
        # Signed value of 8 bits
        return value.decode()
    elif data_type == "xsd_date":
        ## Gregorian calendar date
        _temp_value = parse(value)
        if output == "string":
            _date_format = rdfw().app['kds_dataFormats'].get(\
                    'kds_pythonDateFormat', '')
            return _temp_value.strftime(_date_format)
        elif output == "python":
            return _temp_value
    elif data_type == "xsd_dateTime":
        ## Instant of time (Gregorian calendar)
        _temp_value = parse(value)
        if output == "string":
            _date_format = rdfw().app['kds_dataFormats'].get(\
                    'kds_pythonDateTimeFormat', "%Y-%m-%dT%H:%M:%SZ")
            if _date_format:
                return _temp_value.strftime(_date_format)
            else:
                return str(_temp_value)
        elif output == "python":
            return _temp_value
    elif data_type == "xsd_decimal":
        # Decimal numbers
        return float(value)
    elif data_type == "xsd_double":
        # IEEE 64
        return float(value)
    elif data_type == "xsd_duration":
        # Time durations
        return timedelta(milleseconds=float(value))
    elif data_type == "xsd_ENTITIES":
        # Whitespace
        return value
    elif data_type == "xsd_ENTITY":
        # Reference to an unparsed entity
        return value
    elif data_type == "xsd_float":
        # IEEE 32
        return float(value)
    elif data_type == "xsd_gDay":
        # Recurring period of time: monthly day
        return value
    elif data_type == "xsd_gMonth":
        # Recurring period of time: yearly month
        return value
    elif data_type == "xsd_gMonthDay":
        # Recurring period of time: yearly day
        return value
    elif data_type == "xsd_gYear":
        # Period of one year
        return value
    elif data_type == "xsd_gYearMonth":
        # Period of one month
        return value
    elif data_type == "xsd_hexBinary":
        # Binary contents coded in hexadecimal
        return value
    elif data_type == "xsd_ID":
        # Definition of unique identifiers
        return value
    elif data_type == "xsd_IDREF":
        # Definition of references to unique identifiers
        return value
    elif data_type == "xsd_IDREFS":
        # Definition of lists of references to unique identifiers
        return value
    elif data_type == "xsd_int":
        # 32
        return value
    elif data_type == "xsd_integer":
        # Signed integers of arbitrary length
        return int(value)
    elif data_type == "xsd_language":
        # RFC 1766 language codes
        return value
    elif data_type == "xsd_long":
        # 64
        return int(value)
    elif data_type == "xsd_Name":
        # XML 1.O name
        return value
    elif data_type == "xsd_NCName":
        # Unqualified names
        return value
    elif data_type == "xsd_negativeInteger":
        # Strictly negative integers of arbitrary length
        return abs(int(value))*-1
    elif data_type == "xsd_NMTOKEN":
        # XML 1.0 name token (NMTOKEN)
        return value
    elif data_type == "xsd_NMTOKENS":
        # List of XML 1.0 name tokens (NMTOKEN)
        return value
    elif data_type == "xsd_nonNegativeInteger":
        # Integers of arbitrary length positive or equal to zero
        return abs(int(value))
    elif data_type == "xsd_nonPositiveInteger":
        # Integers of arbitrary length negative or equal to zero
        return abs(int(value))*-1
    elif data_type == "xsd_normalizedString":
        # Whitespace
        return value
    elif data_type == "xsd_NOTATION":
        # Emulation of the XML 1.0 feature
        return value
    elif data_type == "xsd_positiveInteger":
        # Strictly positive integers of arbitrary length
        return abs(int(value))
    elif data_type == "xsd_QName":
        # Namespaces in XML
        return value
    elif data_type == "xsd_short":
        # 32
        return value
    elif data_type == "xsd_string":
        # Any string
        return value
    elif data_type == "xsd_time":
        # Point in time recurring each day
        return parse(value)
    elif data_type == "xsd_token":
        # Whitespace
        return value
    elif data_type == "xsd_unsignedByte":
        # Unsigned value of 8 bits
        return value.decode()
    elif data_type == "xsd_unsignedInt":
        # Unsigned integer of 32 bits
        return int(value)
    elif data_type == "xsd_unsignedLong":
        # Unsigned integer of 64 bits
        return int(value)
    elif data_type == "xsd_unsignedShort":
        # Unsigned integer of 16 bits
        return int(value)
    else:
        return value

def convert_spo_to_dict(data, mode="subject", option="string", method="t-store"):
    '''Takes the SPAQRL query results and converts them to a python Dict

    mode: subject --> groups based on subject
    '''

    def get_o(item, method, option):
        if method == "t-store":
            return xsd_to_python(item['o']['value'], item['o'].get(\
                                "datatype"), item['o']['type'], option)
        elif method == "rdflib":
            return str(item[len(item)-1])


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
def remove_null(obj):
    ''' reads through a list or set and strips any null values'''
    if isinstance(obj, set):
        try:
            obj.remove(None)
        except:
            pass
    elif isinstance(obj, list):
        for item in obj:
            if not is_not_null(item):
                obj.remove(item)
    return obj

class DeleteProperty(object):
    ''' dummy class for tagging items to be deleted. This will prevent
    passed in data ever being confused with marking a property for
    deletion. '''
    def __init__(self):
        setattr(self, "delete", True)

class NotInFormClass(object):
    ''' dummy class for tagging properties that were never in a form.
    This will prevent passed in data ever being confused with a property
    that was never in the form. '''
    def __init__(self):
        setattr(self, "notInForm", True)

def slugify(value):
    """Converts to lowercase, removes non-word characters (alphanumerics and
    underscores) and converts spaces to hyphens. Also strips leading and
    trailing whitespace using Django format

    Args:

    """
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '-', value)

def get_app_ns_uri(value):
    ''' looks in the framework for the namespace uri'''
    for _ns in get_framework().rdf_app_dict['application'].get(\
                                                       "appNameSpace", []):
        if _ns.get('prefix') == value:
            return _ns.get('nameSpaceUri')

def copy_obj(obj):
    ''' does a deepcopy of an object, but does not copy a class
        i.e.
        x = {"key":[<classInstance1>,<classInstance2>,<classInstance3>]}
        y = copy_obj(x)
        y --> {"key":[<classInstance1>,<classInstance2>,<classInstance3>]}
        del y['key'][0]
        y --> {"key":[<classInstance2>,<classInstance3>]}
        x --> {"key":[<classInstance1>,<classInstance2>,<classInstance3>]}
        *** this is to overcome a dictionary object that lists with classes
            as the list items. '''
    if isinstance(obj, dict):
        return_obj = {}
        for key, value in obj.items():
            if isinstance(value, dict):
                return_obj[key] = copy_obj(value)
            elif isinstance(value, list):
                return_obj[key] = copy_obj(value)
            else:
                return_obj[key] = value
    elif isinstance(obj, list):
        return_obj = []
        for value in obj:
            if isinstance(value, dict):
                return_obj.append(copy_obj(value))
            elif isinstance(value, list):
                return_obj.append(copy_obj(value))
            else:
                return_obj.append(value)
    else:
        return_obj = copy.copy(obj)
    return return_obj

def get_attr(item, name, default=None):
    ''' similar to getattr and get but will test for class or dict '''
    if isinstance(item, dict):
        return_val = item.get(name, default)
    else:
        if hasattr(item, name):
            return_val = getattr(item, name)
        else:
            return_val = default
    return return_val

def separate_props(obj):
    ''' will return a obj with the kds_properties as a seprate obj '''
    copied_obj = copy.deepcopy(obj)
    props = copied_obj.get("kds_properties")
    del copied_obj["kds_properties"]
    return({"obj": copied_obj, "kds_properties":props})


def mod_git_ignore(directory, ignore_item, action):
    """ checks if an item is in the specified gitignore file and adds it if it
    is not in the file
    """
    if not os.path.isdir(directory):
        return
    ignore_filepath = os.path.join(directory,".gitignore")
    if not os.path.exists(ignore_filepath):
        items = []
    else:
        with open(ignore_filepath) as ig_file:
            items = ig_file.readlines()
    # strip and clean the lines
    clean_items  = [line.strip("\n").strip() for line in items]
    clean_items = make_list(clean_items)
    if action == "add":
        if ignore_item not in clean_items:
            with open(ignore_filepath, "w") as ig_file:
                clean_items.append(ignore_item)
                ig_file.write("\n".join(clean_items) + "\n")
    elif action == "remove":
        with open(ignore_filepath, "w") as ig_file:
            for i, value in enumerate(clean_items):
                if value != ignore_item.lower():
                    ig_file.write(items[i])

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


class Dot(object):
    """ Takes a dictionary and gets and sets values via a "." dot notation
    of the path
    
    args:
        dictionary: The dictionary object
        copy_dict: Boolean - True - (default) does a deepcopy of the dictionay 
            before returning. False - maniplutes the passed in dictionary
            
    """
    def __init__(self, dictionary, copy_dict=True):
        self.obj = dictionary
        self.new_dict = {}
        self.copy_dict = copy_dict

    def get(self, prop):
        """ get the value off the passed in dot notation
        
        args:
            prop: a string of the property to retreive 
                "a.b.c" ~ dictionary['a']['b']['c']
        """
        prop_parts = prop.split(".")
        val = None
        for part in prop_parts:
            if val is None:
                val = self.obj.get(part)
            else:
                val = val.get(part)
        return val

    def set(self, prop, value):
        """ sets the dot notated property to the passed in value
        
        args:
            prop: a string of the property to retreive 
                "a.b.c" ~ dictionary['a']['b']['c']
            value: the value to set the prop object
        """
        
        prop_parts = prop.split(".")
        if self.copy_dict:
            new_dict = copy.deepcopy(self.obj)
        else:
            new_dict = self.obj
        pointer = None
        parts_length = len(prop_parts) - 1
        for i, part in enumerate(prop_parts):
            if pointer is None and i == parts_length:
                new_dict[part] = value
            elif pointer is None:
                pointer = new_dict.get(part)            
            elif i == parts_length:
                pointer[part] = value
            else:
                pointer = pointer.get(part)
        return new_dict

def rep_int(value):
    """ takes a value and see's if can be converted to an integer

    Args:
        value: value to test
    Returns:
        True or False
    """

    try:
        int(value)
        return True
    except ValueError:
        return False

def delete_key_pattern(obj, regx_pattern):
    ''' takes a dictionary object and a regular expression pattern and removes
    all keys that match the pattern. 
    
    args:
        obj: dictionay object to search trhough
        regx_pattern: string without beginning and ending / '''
    
    if isinstance(obj, list):
        _return_list = []
        for item in obj:
            if isinstance(item, list):
                _return_list.append(delete_key_pattern(item, regx_pattern))
            elif isinstance(item, set):
                _return_list.append(list(item))
            elif isinstance(item, dict):
                _return_list.append(delete_key_pattern(item, regx_pattern))
            else:
                try:
                    json.dumps(item)
                    _return_list.append(item)
                except:
                    _return_list.append(str(type(item)))
        return _return_list
    elif isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, dict):
        _return_obj = {}
        for key, item in obj.items():
            if not re.match(regx_pattern, key):
                if isinstance(item, list):
                    _return_obj[key] = delete_key_pattern(item, regx_pattern)
                elif isinstance(item, set):
                    _return_obj[key] = list(item)
                elif isinstance(item, dict):
                    _return_obj[key] = delete_key_pattern(item, regx_pattern)
                else:
                    try:
                        json.dumps(item)
                        _return_obj[key] = item
                    except:
                        _return_obj[key] = str(type(item))
        return _return_obj
    else:
        try:
            json.dumps(obj)
            return obj
        except:
            return str(type(obj))

def get_dict_key(data, key):
    ''' will serach a mulitdemensional dictionary for a key name and return a 
        value list of matching results '''   
    
    if isinstance(data, Mapping):
        if key in data:
            yield data[key]
        for key_data in data.values():
            for found in get_dict_key(key_data, key):
                yield found

def get_attr(item, name, default=None):
    ''' similar to getattr and get but will test for class or dict '''

    if isinstance(item, dict):
        return_val = item.get(name, default)
    else:
        if hasattr(item, name):
            return_val = getattr(item, name)
        else:
            return_val = default
    return return_val

def copy_obj(obj):
    ''' does a deepcopy of an object, but does not copy a class
        i.e.
        x = {"key":[<classInstance1>,<classInstance2>,<classInstance3>]}
        y = copy_obj(x)
        y --> {"key":[<classInstance1>,<classInstance2>,<classInstance3>]}
        del y['key'][0]
        y --> {"key":[<classInstance2>,<classInstance3>]}
        x --> {"key":[<classInstance1>,<classInstance2>,<classInstance3>]}
        *** this is to overcome a dictionary object that lists with classes
            as the list items. '''

    if isinstance(obj, dict):
        return_obj = {}
        for key, value in obj.items():
            if isinstance(value, dict):
                return_obj[key] = copy_obj(value)
            elif isinstance(value, list):
                return_obj[key] = copy_obj(value)
            else:
                return_obj[key] = value
    elif isinstance(obj, list):
        return_obj = []
        for value in obj:
            if isinstance(value, dict):
                return_obj.append(copy_obj(value))
            elif isinstance(value, list):
                return_obj.append(copy_obj(value))
            else:
                return_obj.append(value)
    else:
        return_obj = copy.copy(obj)
    return return_obj

def get2(item, key, if_none=None, strict=True):
    ''' similar to dict.get functionality but None value will return then 
        if_none value 
     
    args:
        item: dictionary to search
        key: the dictionary key
        if_none: the value to return if None is passed in
        strict: if False an empty string is treated as None'''
        
    if not strict and item.get(key) == "":
        return if_none
    elif item.get(key) is None:
        return if_none
    else:
        return item.get(key)

class IsFirst():
    ''' tracks if is the first time through a loop. class must be initialized
        outside the loop.
        
        *args:
            true -> specifiy the value to return on true
            false -> specify to value to return on false    '''
            
    def __init__(self):
        self.__first = True
        
    def first(self, true=True, false=False):
        if self.__first == True:
            self.__first = False
            return true
        else:
            return false

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

RESERVED_KEYS = ['dict', 
                 'get', 
                 'items', 
                 'keys', 
                 'values', 
                 '_DictClass__reserved']
class DictClass(object):
    ''' takes a dictionary and converts it to a class '''
    __reserved = RESERVED_KEYS

    def __init__(self, obj=None, start=True):
        if obj and start:
            new_class = make_class(obj)
            for attr in dir(new_class):
                if not attr.startswith('__') and attr not in self.__reserved:
                    setattr(self, attr, getattr(new_class,attr))

    def __getattr__(self, attr):
        return None

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        else:
            return None

    def __str__(self):
        return str(self.dict())

    def dict(self):
        """ converts the class to a dictionary object """
        return_obj = {}
        for attr in dir(self):
            if not attr.startswith('__') and attr not in self.__reserved:
                if isinstance(getattr(self, attr), list):
                    return_val = []
                    for item in getattr(self, attr):
                        if isinstance(item, DictClass):
                            return_val.append(dict(item))
                        else:
                            return_val.append(item)
                elif isinstance(getattr(self, attr), dict):
                    return_val = {}
                    for key, item in getattr(self, attr).items():
                        if isinstance(item, DictClass):
                            return_val[key] = item.dict()
                        else:
                            return_val[key] = item
                elif isinstance(getattr(self, attr), DictClass):
                    return_val = getattr(self, attr).dict()
                else:
                    return_val = getattr(self, attr)
                return_obj[attr] = return_val
        return return_obj


    def get(self, attr, none_val=None):
        if hasattr(self, attr):
            return getattr(self, attr)
        else:
            return none_val

    def keys(self):
        return [attr for attr in dir(self) if not attr.startswith("__") and \
                attr not in self.__reserved]

    def values(self):
        return [getattr(self, attr) for attr in dir(self) if not attr.startswith("__") and \
                attr not in self.__reserved]

    def items(self):
        return_list = []
        for attr in dir(self):
            if not attr.startswith("__") and attr not in self.__reserved:
                return_list.append((attr, getattr(self, attr)))
        return return_list

def make_class(obj):
    __reserved = RESERVED_KEYS
    if isinstance(obj, list):
        _return_list = []
        for item in obj:
            if isinstance(item, list):
                _return_list.append(make_class(item))
            elif isinstance(item, set):
                _return_list.append(list(item))
            elif isinstance(item, dict):
                _return_list.append(make_class(item))
            else:
                _return_list.append(item)
        return _return_list
    elif isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, dict):
        new_dict = DictClass(start=False)
        for key, item in obj.items():
            if key in __reserved:
                key += "_1"
            if not key.startswith('__'):
                if isinstance(item, list):
                    setattr(new_dict, key, make_class(item))
                elif isinstance(item, set):
                    setattr(new_dict, key, list(item))
                elif isinstance(item, dict):
                    setattr(new_dict, key, make_class(item))
                else:
                    setattr(new_dict, key, item)
        return new_dict
    else:
        return obj

def fw_config(**kwargs):
    ''' function returns the application configuration information '''
    global FRAMEWORK_CONFIG
    try:
        FRAMEWORK_CONFIG
    except NameError:
        FRAMEWORK_CONFIG = None
    if FRAMEWORK_CONFIG is None:
        if  kwargs.get("config"):
            # if the config is in the form of Mudule convet to a dictionary
            if isinstance(kwargs['config'], ModuleType):
                kwargs['config'] = kwargs['config'].__dict__
            config = kwargs.get("config")
        else:
            try:
                config = current_app.config
            except:
                config = None
        if not config is None:
            FRAMEWORK_CONFIG = make_class(config)
        else:
            print("framework not initialized")
            return "framework not initialized"
    return FRAMEWORK_CONFIG