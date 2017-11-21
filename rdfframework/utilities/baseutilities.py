"""baseutilities.py

Module of helper functions used in the RDF Framework that require no other
framework dependancies

"""
import copy
import datetime
import os
import re
import requests
import pdb
import logging
import inspect

from base64 import b64decode
from flask import json
from jinja2 import Template, Environment, FileSystemLoader
from rdflib import XSD
from dateutil.parser import parse
from rdfframework.utilities import pp

__author__ = "Mike Stabile, Jeremy Nelson"

MNAME = inspect.stack()[0][1]

DEBUG = True

FRAMEWORK_BASE = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

ENV = Environment(loader=FileSystemLoader(
    [os.path.join(FRAMEWORK_BASE, "sparql", "queries"),
     os.path.join(FRAMEWORK_BASE, "turtle")]))

def pyfile_path(path):
    """ converst a file path argment to the is path within the framework

    args:
        path: filepath to the python file
    """
    if "/" in path:
        parts = path.split("/")
        join_term = "/"
    elif "\\" in path:
        parts =path.split("\\")
        join_term = "\\"
    parts.reverse()
    base = parts[:parts.index('rdfframework')]
    base.reverse()
    return join_term.join(base)

def pick(*args):
    """ Returns the first non None value of the passed in values """
    for item in args:
        if item is not None and not isinstance(item, EmptyDot):
            return item
    return None

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
            elif value.lower() in ['false', '0', 'n', 'no', 'f']:
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


def slugify(value):
    """Converts to lowercase, removes non-word characters (alphanumerics and
    underscores) and converts spaces to hyphens. Also strips leading and
    trailing whitespace using Django format

    Args:

    """
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '-', value)


def copy_obj(obj):
    ''' does a deepcopy of an object, but does not copy a class
        i.e.
        x = {"key":[<classInstance1>,<classInstance2>,<classInstance3>]}
        y = copy_obj(x)
        y --> {"key":[<classInstance1>,<classInstance2>,<classInstance3>]}
        del y['key'][0]
        y --> {"key":[<classInstance2>,<classInstance3>]}
        x --> {"    key":[<classInstance1>,<classInstance2>,<classInstance3>]}
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

class DictClassMeta(type):
    """ Used to handle list generation """

    def __call__(cls, *args, **kwargs):

        new_class = False
        if len(args) > 0:
            new_class = make_class(args[0], kwargs.get('debug',False))
        if new_class and isinstance(new_class, list):
            return new_class
        elif len(args) > 0:
            vals = list(args)
            vals[0] = new_class
            vals = tuple(vals)
        else:
            vals = args
        return super().__call__(*vals, **kwargs)

RESERVED_KEYS = ['dict',
                 'get',
                 'items',
                 'keys',
                 'values',
                 '_DictClass__reserved',
                 '_RdfConfigManager__reserved',
                 '_RdfConfigManager__type',
                 '_DictClass__type',
                 'debug',
                 '_RdfConfigManager__load_config']

class DictClass(metaclass=DictClassMeta):
    ''' takes a dictionary and converts it to a class '''
    __reserved = RESERVED_KEYS
    __type = 'DictClass'

    def __init__(self, obj=None, start=True, debug=False):
        if obj and start:
            for attr in dir(obj):
                if not attr.startswith('_') and attr not in self.__reserved:
                    setattr(self, attr, getattr(obj,attr))

    def __getattr__(self, attr):
        return None

    def __getitem__(self, item):
        item = str(item)
        if hasattr(self, item):
            return getattr(self, item)
        else:
            return None

    def __setitem__(self, attr, value):
        self.__setattr__(attr, value)

    def __str__(self):
        return str(self.dict())

    def __repr__(self):
        return "DictClass(\n%s\n)" % pp.pformat(self.dict())

    def __setattr__(self, attr, value):
        if isinstance(value, dict) or isinstance(value, list):
            value = DictClass(value)
        self.__dict__[attr] = value

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


    def get(self, attr, none_val=None, strict=False):
        if attr in self.keys():
            if strict and self[attr] is None:
                return none_val
            else:
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

def make_class(obj, debug=False):
    __reserved = RESERVED_KEYS
    if isinstance(obj, list):
        _return_list = []
        for item in obj:
            if isinstance(item, list):
                _return_list.append(make_class(item, debug))
            elif isinstance(item, set):
                _return_list.append(list(item))
            elif isinstance(item, dict):
                _return_list.append(make_class(item, debug))
            else:
                _return_list.append(item)
        #pdb.set_trace()
        return _return_list
    elif isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, dict):
        new_dict = DictClass(start=False)
        for key, item in obj.items():
            if debug: pdb.set_trace()
            if key in __reserved:
                key += "_1"
            if not key.startswith('__'):
                if debug: pdb.set_trace()
                if isinstance(item, list):
                    if debug: pdb.set_trace()
                    setattr(new_dict, key, make_class(item, debug))
                elif isinstance(item, set):
                    if debug: pdb.set_trace()
                    setattr(new_dict, key, list(item))
                elif isinstance(item, dict):
                    if debug: pdb.set_trace()
                    setattr(new_dict, key, make_class(item, debug))
                else:
                    if debug: pdb.set_trace()
                    setattr(new_dict, key, item)
        return new_dict
    else:
        return obj

class EmptyDot():
    def __getattr__(self, attr):
        return EmptyDot()

    def __repr__(self):
        return ""
