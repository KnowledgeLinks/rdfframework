__author__ = "Mike Stabile, Jeremy Nelson"

import sys
import os
import pdb
import pprint
import json
import types
import inspect
from hashlib import sha1


from rdfframework.utilities import RdfNsManager, render_without_request, \
                                   RdfConfigManager, make_doc_string, \
                                   p_args, LABEL_FIELDS, VALUE_FIELDS, \
                                   DESCRIPTION_FIELDS, find_values
from rdfframework.rdfdatatypes import BaseRdfDataType, Uri, DT_LOOKUP, BlankNode

CFG = RdfConfigManager()
NSM = RdfNsManager()
MODULE = __import__(__name__)

# List of class names that will be excluded when examining the bases of a class
IGNORE_CLASSES = ['RdfClassBase', 'dict', 'list']

def print_doc(self=None):
    print(self.__doc__)

def remove_parents(bases):
            """ removes the parent classes if one base is subclass of
                another"""
            remove_i = []
            for i, base in enumerate(bases):
                for j, other in enumerate(bases):
                    if issubclass(base, other) and j != i:
                        remove_i.append(i)
            remove_i = set(remove_i)
            remove_i = [i for i in remove_i]
            remove_i.reverse()
            for index in remove_i:
                try:
                    del(bases[index])
                except IndexError:
                    print("Unable to delete base: ", bases)
            return bases

def get_properties(cls_def):
    """ cycles through the class definiton and returns all properties """
    # pdb.set_trace()
    prop_list = {prop: value for prop, value in cls_def.items() \
                 if 'rdf_Property' in value.get('rdf_type',"") or \
                 value.get('rdfs_domain')}

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

def prepare_prop_defs(prop_defs, prop_name, cls_name):
    """ Examines and adds any missing defs to the prop_defs dictionary

    args:
        prop_defs: the defintions from the rdf vocabulary defintion

    returns:
        prop_defs
    """
    required_def_defaults = {
        Uri('kds_rangeDef'): [{}],
        Uri('rdfs_range'): [Uri("xsd_string")],
        Uri('rdfs_domain'): [Uri(cls_name)],
        Uri('rdfs_label'): [NSM.nouri(prop_name)],
        Uri('kds_formDefault'): [{
            Uri('kds:classUri'): Uri('kdr:AllClasses'),
            Uri('kds:formFieldName'): "emailaddr",
            Uri('kds:formLabelName'): [NSM.nouri(prop_name)],
            Uri('kds:formFieldHelp'): find_values(DESCRIPTION_FIELDS,
                                                   prop_defs,
                                                   None),
            Uri('kds:fieldType'): {
                Uri('rdf:type'): Uri('kdr:TextField')
            }
        }],
        Uri('kds_propertyValidation'): [],
        Uri('kds_propertySecurity'): [],
        Uri('kds_propertyProcessing'): []
    }
    rtn_dict = {}
    for prop in required_def_defaults.keys():
        if prop not in prop_defs.keys():
            prop_defs[prop] = required_def_defaults[prop]
    return prop_defs

def unique_append(self, value):
    if value not in self:
        super(self.__class__, self).append(Uri(value))

class RdfPropertyMeta(type):
    @classmethod
    def __prepare__(*args, **kwargs):
        # print('  RdfClassMeta.__prepare__(\n\t\t%s)' % (p_args(args, kwargs)))
        
        prop_defs = kwargs.pop('prop_defs')
        prop_name = kwargs.pop('prop_name')
        cls_name = kwargs.pop('cls_name')
        if cls_name == 'RdfClassBase':
            return {}
        doc_string = make_doc_string(args[1],
                                     prop_defs,
                                     args[2],
                                     None)        
        new_def = prepare_prop_defs(prop_defs, prop_name, cls_name)
        new_def['__doc__'] = doc_string
        new_def['_cls_name'] = cls_name
        new_def['_prop_name'] = prop_name
        if prop_name == 'rdf_type':
            new_def['append'] = unique_append
        # pdb.set_trace()
        return new_def

    def __new__(meta, name, bases, clsdict, **kwds):
        return super().__new__(meta, name, bases, clsdict)

    def __init__(self, *args, **kwargs):
        pass

class RdfPropertyBase(list): #  metaclass=RdfPropertyMeta):
    """ Property Base Class """
    def __init__(self, bound_class, dataset=None):
        self.dataset = dataset
        self.bound_class = bound_class
        self.old_data = []

    def __call__(self, bound_class, dataset=None):
        self.dataset = dataset
        self.bound_class = bound_class
        self.old_data = []

    @classmethod
    def es_mapping(cls, base_class, **kwargs):
        """ Returns the es mapping for the property
        """
        es_idx_types = {
            'es_Raw': {'keyword': {'type': 'keyword'}}, 
            'es_Lower': {'lower': {'type': 'text', 
                                   'analyzer': 'keylower'}},
            'es_NotAnalyzed': "keyword",
            'es_NotIndexed': False
        }
        # if cls._prop_name == 'dcterm_created':
        #     pdb.set_trace()
        es_map = {}
        ranges = cls.rdfs_range
        rng_defs = [rng_def for rng_def in cls.kds_rangeDef \
                    if not isinstance(rng_def, BlankNode) \
                    and (cls._cls_name in rng_def.get('kds_classUri',[]) \
                    or 'kdr_AllClasses' in rng_def.get('kds_classUri',[]))]

        if len(rng_defs) > 1:
            pass 
            #! write function to merge range defs
        try:
            rng_def = rng_defs[0]
        except IndexError:
            rng_def = {}
        idx_types = rng_def.get('kds_esIndexType',[]).copy()
        # pdb.set_trace()
        try:
            idx_types.remove('es_Standard')
        except ValueError:
            pass
        if cls._prop_name == "rdfs_label":
            idx_types += ['es_Raw', 'es_Lower'] 
        if len(idx_types) == 0:
            nested = False
            for rng in ranges:
                if hasattr(MODULE.rdfclass, rng) and \
                        rng != 'rdfs_Literal' and \
                        isinstance(getattr(MODULE.rdfclass, rng), RdfClassMeta)\
                        and cls._prop_name != 'rdf_type':
                    nested = True
            if nested:
                idx_types.append('es_Nested')
        if 'es_Nested' in idx_types:
            if (kwargs.get('depth',0) >= 1 and \
                    kwargs.get('class') == ranges[0]) or kwargs.get('depth',0) > 2:
                return {"type" : "keyword"}
            # pdb.set_trace()
            # if cls._prop_name == 'bf_eventContent':
            #     pdb.set_trace() 
            nested_map = getattr(MODULE.rdfclass,
                    ranges[0]).es_mapping(base_class, 'es_Nested', **kwargs)
            es_map['properties'] = nested_map
            # es_map['properties'] = 
            es_map['type'] = "nested"
        elif len(idx_types) > 1:
            fields = {}
            for idx in idx_types:
                fields.update(es_idx_types[idx])
            es_map['fields'] = fields
        elif len(idx_types) == 1:
            if cls._prop_name == 'rdf_type':
                es_map['type'] = 'keyword'
            elif idx_types[0] == 'es_NotIndexed':
                es_map['index'] = False
            else:
                es_map['type'] = es_idx_types[idx_types[0]]
        try:
            if not es_map.get('type'):
                fld_type = DT_LOOKUP.get(ranges[0]).es_type
                es_map['type'] = fld_type
                if cls._prop_name == 'rdf_type':
                    es_map['type'] = 'keyword'
        except (KeyError, AttributeError):
            if cls._prop_name == 'rdf_type':
                es_map['type'] = 'keyword'
            else:
                es_map['type'] = 'text'
        if es_map['type'] == "nested":
            del es_map['type']
        try:
            fld_format = DT_LOOKUP.get(ranges[0]).es_format
            es_map['format'] = fld_format
        except (KeyError, AttributeError):
            pass
        return es_map

    def es_json(self, **kwargs):
        """ Returns a JSON object of the property for insertion into es
        """

        def _convert_value(value, method=None):

            def _sub_convert(val):
                if isinstance(val, BaseRdfDataType):
                    return val.to_json
                elif isinstance(value, RdfClassBase):
                    return val.subject.sparql_uri
                else:
                    return val

            if method == "missing_obj":
                rtn_obj = {
                        "rdf_type": [rng.sparql_uri for rng in self.rdfs_range],
                        "label": [getattr(self, label)[0] \
                                  for label in LABEL_FIELDS \
                                  if hasattr(self, label)][0]}
                try:
                    rtn_obj['uri'] = value.sparql_uri
                    rtn_obj["rdfs_label"] = NSM.nouri(value.sparql_uri)
                except AttributeError:
                    rtn_obj['uri'] ="None Specified"
                    rtn_obj['rdfs_label'] = _sub_convert(value)
                rtn_obj['value'] = rtn_obj['rdfs_label']
                return rtn_obj
            else:
                return _sub_convert(value)

            

        try:
            rng_defs = [rng_def for rng_def in self.kds_rangeDef \
                        if not isinstance(rng_def, BlankNode) \
                        and (self._cls_name in rng_def.get('kds_classUri',[]) \
                        or 'kdr_AllClasses' in rng_def.get('kds_classUri',[]))]
        except AttributeError:
            rng_defs = []

        if len(rng_defs) > 1:
            pass 
            #! write function to merge range defs
        try:
            rng_def = rng_defs[0]
        except IndexError:
            rng_def = {}
        idx_types = rng_def.get('kds_esIndexType',[]).copy()
        rtn_list = []
        ranges = self.rdfs_range
        # if self._prop_name == 'bf_shelfMark':
        #     pdb.set_trace()
        if len(idx_types) == 0:
            nested = False
            for rng in ranges:
                if hasattr(MODULE.rdfclass, rng) and \
                        rng != 'rdfs_Literal' and \
                        isinstance(getattr(MODULE.rdfclass, rng),
                                   RdfClassMeta):
                    nested = True
            for value in self:
                if isinstance(value, RdfClassBase):
                    nested = True
            if nested:
                idx_types.append('es_Nested')

        if 'es_Nested' in idx_types:
            if kwargs.get('depth',0) > 6:
                return  [val.subject.sparql_uri for val in self]
            for value in self:
                # if self._prop_name == "bf_shelfMark":
                #     pdb.set_trace()
                try:
                    rtn_list.append(value.es_json('es_Nested', **kwargs))
                except AttributeError:
                    rtn_list.append(_convert_value(value, 
                                                   "missing_obj"))
        else:
            for value in self:
                # if value.__class__.__name__ == "bf_shelfMark":
                #     pdb.set_trace()
                rtn_list.append(_convert_value(value))
        return rtn_list


def make_property(prop_defs, prop_name, cls_name):
    """ Generates a property class from the defintion dictionary

        args:
            prop_defs: the dictionary defining the property
            prop_name: the base name of the property
            cls_name: the name of the rdf_class with which the property is 
                      associated
    """
    if cls_name != 'RdfBaseClass':
        new_name = "%s_%s" % (prop_name, cls_name)
        prop_defs['kds_classUri'] = Uri(cls_name)
    else:
        new_name = prop_name

    return types.new_class(new_name,
                           (RdfPropertyBase, list,),
                           {'metaclass': RdfPropertyMeta,
                            'prop_defs': prop_defs,
                            'cls_name': cls_name,
                            'prop_name': prop_name})

def list_hierarchy(class_name, bases):
    """ creates a list of the class hierarchy

    args:
        class_name: name of the current class
        bases: list/tuple of bases for the current class
    """

    class_list = [Uri(class_name)]
    for base in bases:
        if base.__name__ not in IGNORE_CLASSES:
            class_list.append(Uri(base.__name__))
    return list([i for i in set(class_list)])

def es_get_class_defs(cls_defs, cls_name):
    """ reads through the class defs and gets the related es class 
        defintions

    Args:
        class_defs: RdfDataset of class definitions
    """
    
    cls_def = cls_defs[cls_name]
    rtn_dict = {key: value for key, value in cls_def.items() \
                if key.startswith("kds_es")}
    for key in rtn_dict.keys():
        del cls_defs[cls_name][key]
    return rtn_dict


def list_properties(cls):
        """ returns a dictionary of properties assigned to the class"""
        rtn_dict = {}
        for attr in dir(cls):
            if attr not in ["properties", "__doc__", "doc"]:
                attr_val = getattr(cls, attr)

                if isinstance(attr_val, RdfPropertyMeta):
                    rtn_dict[attr] = attr_val
        return rtn_dict

class RdfClassMeta(Registry):

    @property
    def doc(self):  
        print_doc(self)

    @property
    def properties(self):
        return list_properties(self)

    @classmethod
    def __prepare__(*args, **kwargs):
        # print('  RdfClassMeta.__prepare__(\n\t\t%s)' % (p_args(args, kwargs)))
        # pdb.set_trace()
        try:
            # if args[1] == 'bf_Work':
            #     pdb.set_trace()
            cls_defs = kwargs.pop('cls_defs') #CFG.rdf_class_defs.get(args[1],{})
            props = get_properties(cls_defs)
            # pdb.set_trace()
            doc_string = make_doc_string(args[1],
                                        cls_defs[args[1]],
                                        args[2],
                                        props)
            new_def = {}
            new_def['__doc__'] = doc_string
            new_def['doc'] = property(print_doc)
            new_def['properties'] = property(list_properties)
            new_def['json_def'] = cls_defs
            new_def['hierarchy'] = list_hierarchy(args[1], args[2])
            new_def['id'] = None
            es_defs = es_get_class_defs(cls_defs, args[1])
            if len(es_defs) > 0 and not hasattr(args[2][0], 'es_defs'):
                new_def['es_defs'] = es_defs
            new_def['es_defs'] = es_defs
            new_def['uri'] = Uri(args[1]).sparql_uri
            # pdb.set_trace()
            for prop, value in props.items():
                new_def[prop] = make_property(value, prop, args[1])
            # pdb.set_trace()
            if 'rdf_type' not in new_def.keys():
                new_def[Uri('rdf_type')] = make_property({},
                                                         'rdf_type',
                                                         args[1])
            new_def['cls_defs'] = cls_defs.pop(args[1])
            # if args[1] == 'bf_Topic':
            #     pdb.set_trace()
            return new_def
        except KeyError:
            return {}

    def __new__(meta, name, bases, clsdict, **kwds):
        return super().__new__(meta, name, bases, clsdict)

    def __init__(self, *args, **kwargs):
        pass

class RdfClassBase(dict, metaclass=RdfClassMeta):

    

    uri_format = 'sparql_uri'

    def __init__(self, sub, **kwargs):
        # if not hasattr(self, "properties"):
        #     self.properties = {}
        self.dataset = kwargs.get('dataset')
        # if not kwargs.get("def_load"):
        self._initilize_props()
        # if kwargs.get("debug"):
        #     pdb.set_trace()
        if isinstance(sub, dict):
            self.subject = sub['s']
            if isinstance(sub['o'], list):
                for item in sub['o']:
                    self.add_property(sub['p'], item, kwargs.get("obj_method"))
            else:
                self.add_property(sub['p'], sub['o'], kwargs.get("obj_method"))
        else:
            self.subject = Uri(sub)
        
    def _initilize_props(self, **kwargs):
        """ Adds an intialized property to the class dictionary """
        try:
            for prop, prop_class in self.properties.items():
                # passing in the current dataset tie
                self[prop] = prop_class(self, self.dataset)
            bases = remove_parents(self.__class__.__bases__)
            for base in bases:
                if base.__name__ not in IGNORE_CLASSES:
                    base_name = Uri(base.__name__)
                    try:
                        self['rdf_type'].append(base_name)
                    except KeyError:
                        self[Uri('rdf_type')] = make_property({},
                                'rdf_type', self.__class__.__name__)\
                                (self, self.dataset)
                        self['rdf_type'].append(base_name)
        except (AttributeError, TypeError):
            pass

    def add_property(self, pred, obj, obj_method=None, **kwargs):
        """ adds a property and its value to the class instance

        args:
            pred: the predicate/property to add
            obj: the value/object to add
            obj_method: *** No longer in used.
        """
        pred = Uri(pred)
        try:
            self[pred].append(obj)
        except AttributeError:
            new_list = [self[pred]]
            new_list.append(obj)
            self[pred] = new_list
        except KeyError:
            setattr(self,
                    pred, 
                    make_property({},pred, self.__class__.__name__))                                
            self[pred] = getattr(self, pred)(self, self.dataset)
            self[pred].append(obj)

    @property
    def subclasses(self):
        """ returns a list of sublcasses to the current class """
        return Registry[self.__class__.__name__]

    @property
    def to_json(self, start=True):
        return self.conv_json(self.uri_format)

    def conv_json(self, uri_format="sparql_uri", add_ids=False):

        def convert_item(ivalue):
            nvalue = ivalue
            # pdb.set_trace()
            if isinstance(ivalue, BaseRdfDataType):
                if ivalue.type == 'uri':
                    if ivalue.startswith("pyuri") and uri_format == "pyuri":
                        nvalue = getattr(ivalue, "sparql")
                    else:
                        nvalue = getattr(ivalue, uri_format)
                else:
                    nvalue = ivalue.to_json
            # elif isinstance(ivalue, RdfPropertyBase):
            #     pdb.set_trace()
            elif isinstance(ivalue, RdfClassBase):
                if ivalue.subject.type == "uri":
                    # nvalue = getattr(ivalue.subject, uri_format)
                    nvalue = ivalue.conv_json(uri_format, add_ids)
                elif ivalue.subject.type == "bnode":
                    nvalue = ivalue.conv_json(uri_format, add_ids)
            elif isinstance(ivalue, list):
                nvalue = []
                for item in ivalue:
                    temp = convert_item(item)
                    nvalue.append(temp)
            return nvalue

        rtn_val = {key: convert_item(value) for key, value in self.items()}
        #pdb.set_trace()
        if add_ids:
            
            if self.subject.type == 'uri':
                rtn_val['uri'] = self.subject.sparql_uri
                rtn_val['id'] = sha1(rtn_val['uri'].encode()).hexdigest()
        #return {key: convert_item(value) for key, value in self.items()}
        return rtn_val

    @classmethod
    def es_mapping(cls, base_class, role='rdf_Class', **kwargs):
        """ Returns the es mapping for the class

        args:
            role: the role states how the class should be mapped depending
                  upon whether it is used as a subject of an object. options
                  are es_Nested or rdf_Class
        """

        def _prop_filter(prop, value, kwargs):
            try:
                use_prop = len(set(value.owl_inverseOf) - parent_props) > 0
            except AttributeError:
                use_prop = True
            # if prop == 'bf_eventContentOf':
            #     pdb.set_trace()
            if not use_prop:
                print(prop)
            if prop in nested_props and use_prop:
                return True
            else:
                return False

        es_map = {}
        if kwargs.get("depth"): # and kwargs.get('class') == cls.__name__:
            kwargs['depth'] += 1
        else:
            kwargs['depth'] = 1
            kwargs['class'] = cls.__name__
            kwargs['class_obj'] = cls
        if kwargs.get('class_obj'):
            parent_props = set(cls.properties)
        else:
            parent_props = set()
        if role == 'rdf_Class':
            es_map = {}
            es_map = {prop: value.es_mapping(base_class) \
                      for prop, value in cls.properties.items()}
            # for prop, value in cls.properties.items():
            #     if prop == "bf_instanceOf":
            #         try:
            #             use_prop = len(set(value.owl_inverseOf) - parent_props) > 1
            #         except AttributeError:
            #             use_prop = True
            #         print("\n****** ", prop," use_prop: ", use_prop,"\n")
            #         pdb.set_trace()
            #         print(value.es_mapping())
            #     else:
            #         x = value.es_mapping()


        elif role == 'es_Nested':
            # print(locals())
            # pdb.set_trace()
            if cls == base_class:
                nested_props = LABEL_FIELDS
            else:
                nested_props = cls.es_defs.get('kds_esNestedProps',
                        list(cls.properties.keys()))
            # es_map = {prop: value.es_mapping(**kwargs) \
            #           for prop, value in cls.properties.items() \
            #           if prop in kds_esNestedProps and \
            #           not prop.endswith('Of')}
            es_map = {prop: value.es_mapping(base_class, **kwargs) \
                      for prop, value in cls.properties.items() \
                      if _prop_filter(prop, value, kwargs)}
            # for prop, value in cls.properties.items():
            #     if prop == "bf_instanceOf":
            #         try:
            #             use_prop = len(set(value.owl_inverseOf) - parent_props) > 1
            #         except AttributeError:
            #             use_prop = True
            #         print("\n****** ", prop," use_prop: ", use_prop,"\n")
            #         pdb.set_trace()
            #         print(value.es_mapping(**kwargs))
            #     else:
            #         x = value.es_mapping(**kwargs)
        ref_map = {
            "type" : "keyword"
        }
        ignore_map = {
            "index": False,
            "include_in_all": False,
            "type": "text"
        }
        es_map['label'] = ref_map
        es_map['value'] = ref_map

        if cls.cls_defs.get('kds_storageType') != "blanknode":
            es_map['id'] = ref_map
            es_map['uri'] = ref_map
            if role == 'rdf_Class':
                es_map['turtle'] = ignore_map
        return es_map


    def es_json(self, role='rdf_Class', remove_empty=True, **kwargs):
        """ Returns a JSON object of the class for insertion into es

        args:
            role: the role states how the class data should be returned
                  depending upon whether it is used as a subject of an object. 
                  options are kds_esNested or rdf_Class
        """
        # value_field = [cls.es_defs.get(kds_esValue), 
        #                cls.es_defs.get(kds_esAltValue)]
        # value_field = [item for item in value_field if item is not None]
        # if len(value_field) == 0:
        #     value_field = ['skos_prefLabel',
        #                    'schema_name',
        #                    'skos_altLabel',
        #                    'schema_alternateName',
        #                    'foaf_labelproperty',
        #                    'rdfs_label',
        #                    'hiddenlabel']
        rtn_obj = {}
        # pdb.set_trace()
        if kwargs.get("depth"):
            kwargs['depth'] += 1
        else:
            kwargs['depth'] = 1
        if role == 'rdf_Class':
            for prop, value in self.items():
                new_val = value.es_json()
                if (remove_empty and len(new_val) > 0) or not remove_empty:
                    if len(new_val) == 1:
                        rtn_obj[prop] = new_val[0]
                    else:
                        rtn_obj[prop] = new_val
        else:
            try:
                nested_props = self.es_defs.get('kds_esNestedProps',
                                                list(self.keys()))
            except AttributeError:
                nested_props = list(self.keys())
            for prop, value in self.items():
                if prop in nested_props:
                    # if prop == 'bf_shelfMark':
                    #     pdb.set_trace()
                    new_val = value.es_json(**kwargs)
                    if (remove_empty and len(new_val) > 0) or not remove_empty:
                        if len(new_val) == 1:
                            rtn_obj[prop] = new_val[0]
                        else:
                            rtn_obj[prop] = new_val

        if self.subject.type == 'uri':
            rtn_obj['uri'] = self.subject.sparql_uri
            try:
                path = ""
                for base in [self.__class__] + list(self.__class__.__bases__):
                    
                    if hasattr(base, 'es_defs') and len(base.es_defs) > 0:
                        path = "%s/%s/" % (base.es_defs['kds_esIndex'][0],
                                           base.es_defs['kds_esDocType'][0])
                        continue
            except KeyError:
                path = ""
            rtn_obj['id'] = path + sha1(rtn_obj['uri'].encode()).hexdigest()
        try:
            rtn_obj['label'] = [self.cls_defs[label][0] \
                                for label in LABEL_FIELDS \
                                if self.cls_defs.get(label)][0]
        except IndexError:
            print("Missing class label: ", self.__class__.__name__)
            rtn_obj['label'] = self.__class__.__name__.split("_")[-1]
        try:
            rtn_obj['value'] = [rtn_obj.get(label) \
                                for label in VALUE_FIELDS + LABEL_FIELDS \
                                if rtn_obj.get(label)][0]
        except IndexError:
            rtn_obj['value'] = ", ".join(["%s: %s" % (value.get('label'), value.get('value')) \
                                for prop, value in rtn_obj.items() \
                                if isinstance(value, dict) and \
                                value.get('label')])
        if rtn_obj['value'].strip().endswith("/"):
            rtn_obj['value'] = rtn_obj['value'].strip()[:-1].strip()
        return rtn_obj


# import re
# import json
# import requests
# import copy
# import pdb
# from werkzeug.datastructures import FileStorage
# from jinja2 import Template
# from hashlib import sha1
# #from rdfframework import fw_config
# try:
#     from rdfframework.utilities import clean_iri, iri, is_not_null, \
#         make_list, make_set, make_triple, remove_null, DeleteProperty, \
#         NotInFormClass, pp, uri, calculate_default_value, uri_prefix, nouri, \
#         pyuri, get_attr, slugify, RdfConfigManager
# except ImportError:
#     # Try local imports
#     from .utilities import clean_iri, iri, is_not_null, \
#         make_list, make_set, make_triple, remove_null, DeleteProperty, \
#         NotInFormClass, pp, uri, calculate_default_value, uri_prefix, nouri, \
#         pyuri, get_attr, slugify, RdfConfigManager
   

# from .getframework import get_framework as rdfw
# try:
#     from rdfframework.rdfdatatypes import BaseRdfDataType
#     from rdfframework.rdfdatatype import RdfDataType
#     from rdfframework.utilities.debug import dumpable_obj
#     from rdfframework.processors import clean_processors, run_processor
#     from rdfframework.sparql import save_file_to_repository
# except ImportError:
#     # Try local imports
#     from .rdfdatatype import RdfDataType
#     from .utilities.debug import dumpable_obj
#     from .processors import clean_processors, run_processor
#     from .sparql import save_file_to_repository
#     from .rdfdatatypes import BaseRdfDataType
   
# setting DEBUG to False will turn all the debug printing off in the module

# class RdfBaseClass(dict):
#     # _reserved = ['add_property',
#     #              '_format',
#     #              '_reserved',
#     #              'subject',
#     #              '_type',
#     #              'to_json',
#     #              'uri_format',
#     #              'conv_json']

#     # __slots__ = ['subject']

#     uri_format = 'sparql_uri'

#     def __init__(self, sub, **kwargs):
#         if isinstance(sub, dict):
#             self.subject = sub
#             self.add_property(sub['p'], sub['o'], kwargs.get("obj_method"))
#         else:
#             self.subject = {"s":sub, "p":None, "o":None}
            

#     def add_property(self, pred, obj, obj_method=None):
#         try:
#             self[pred].append(obj)
#         except AttributeError:
#             new_list = [self[pred]]
#             new_list.append(obj)
#             self[pred] = new_list
#         except KeyError:
#             if obj_method != "list":
#                 self[pred] = obj
#             else:
#                 self[pred] = [obj]

#     @property
#     def to_json(self, start=True):
#         return self.conv_json(self.uri_format)

#     def conv_json(self, uri_format="sparql_uri", add_ids=False):

#         def convert_item(ivalue):
#             nvalue = ivalue
#             if isinstance(ivalue, BaseRdfDataType):
#                 if ivalue.type == 'uri':
#                     if ivalue.startswith("pyuri") and uri_format == "pyuri":
#                         nvalue = getattr(ivalue, "sparql")
#                     else:
#                         nvalue = getattr(ivalue, uri_format)
#                 else:
#                     nvalue = ivalue.to_json
#             elif isinstance(ivalue, RdfBaseClass):
#                 if ivalue.subject['s'].type == "uri":
#                     # nvalue = getattr(ivalue.subject['s'], uri_format)
#                     nvalue = ivalue.conv_json(uri_format, add_ids)
#                 elif ivalue.subject['s'].type == "bnode":
#                     nvalue = ivalue.conv_json(uri_format, add_ids)
#             elif isinstance(ivalue, list):
#                 nvalue = []
#                 for item in ivalue:
#                     temp = convert_item(item)
#                     nvalue.append(temp)
#             return nvalue

#         rtn_val = {key: convert_item(value) for key, value in self.items()}
#         #pdb.set_trace()
#         if add_ids:
            
#             if self.subject['s'].type == 'uri':
#                 rtn_val['uri'] = self.subject['s'].sparql_uri
#                 rtn_val['id'] = sha1(rtn_val['uri'].encode()).hexdigest()
#         #return {key: convert_item(value) for key, value in self.items()}
#         return rtn_val

# DEBUG = True
# class RdfClass(object):
#     ''' RDF Class for an RDF Class object.
#         Used for manipulating and validating an RDF Class subject'''


#     def __init__(self, json_obj, class_name, **kwargs):
#         if not DEBUG:
#             debug = False
#         else:
#             debug = False
#         if debug: print("\nSTART RdfClass.init ---------------------------\n")
#         self.class_name = None
#         self.kds_properties = {}
#         for _prop in json_obj:
#             setattr(self, _prop, json_obj[_prop])
#         setattr(self, "class_name", class_name)
#         # The below accounts for cases where we may be using more than one
#         # repository or triplestore

#         # The 'kds_triplestoreConfigName' is the variable name in the
#         # config file that specifies the URL of the triplestore
#         if not hasattr(self, "kds_triplestoreConfigName"):
#             self.kds_triplestoreConfigName = "TRIPLESTORE_URL"
#         if not hasattr(self, "kds_repositoryConfigName"):
#             self.kds_repositoryConfigName = "REPOSITORY_URL"
#         # The kds_saveLocation specifies where to save the data i.e.
#         # in the triplestore or the repository
#         if not hasattr(self, "kds_saveLocation"):
#             self.kds_saveLocation = kwargs.get("kds_saveLocation",
#                                                "triplestore")
#         # The kds_queryLocation specifies where to query for class data
#         if not hasattr(self, "kds_queryLocation"):
#             self.kds_queryLocation = "triplestore"
#         # set the triplestore and repository urls for the class
#         self.triplestore_url = fw_config().get(self.kds_triplestoreConfigName)
#         self.repository_url = fw_config().get(self.kds_repositoryConfigName)
#         if not hasattr(self, "kdssubjectPattern"):
#             self.kdssubjectPattern = kwargs.get("kdssubjectPattern",
#                     "!--baseUrl,/,ns,/,!--classPrefix,/,!--className,/,!--uuid")
#         if not hasattr(self, "kds_baseUrl"):
#             self.kds_baseUrl = kwargs.get("kds_baseUrl", fw_config().get(\
#                 "ORGANIZATION",{}).get("url", "NO_BASE_URL"))
#         if debug: pp.pprint(self.__dict__)
#         if debug: print("\nEND RdfClass.init ---------------------------\n")

#     def save(self, rdf_obj, validation_status=True):
#         """Method validates and saves passed data for the class

#         Args:
#             rdf_obj -- Current RDF Form class fields
#             validationS

#         valid_required_props = self._validate_required_properties(
#             rdf_obj,
#             old_form_data)
#         validDependancies = self._validate_dependant_props(
#             rdf_obj,
#             old_form_data)"""

#         if not DEBUG:
#             debug = False
#         else:
#             debug = True
#         if debug: print("START RdfClass.save ---------------------------\n")
#         if debug: print("kds_classUri: ", self.kds_classUri, "  ************")
#         if not validation_status:
#             return self.validate_form_data(rdf_obj)
#         _class_obj_props = rdf_obj.class_grouping.get(self.kds_classUri,[])
#         expanded_prop_list = []
#         nonlist_prop_list = []
#         for prop in _class_obj_props:
#             if get_attr(prop, "type") == 'FieldList':
#                 for entry in prop.entries:
#                     new_prop = copy.copy(prop)
#                     new_prop.data = entry.data
                    
#                     if debug: print("* * * * * ", prop.name,": ",entry.data)
#                     expanded_prop_list.append(new_prop)
#             else:
#                 nonlist_prop_list.append(prop)
#         list_save_multi = []
#         for prop in expanded_prop_list:
#             list_save_multi.append([prop] + nonlist_prop_list)
#         if len(list_save_multi) > 0:
#             save_results = []
#             for class_props in list_save_multi:
#                 save_data = self._process_class_data(rdf_obj, class_props=class_props)
#                 if debug: print("-------------- Save data:\n",pp.pprint(save_data))
#                 save_query = self._generate_save_query(save_data)
#                 if debug: print("save_query: \n", pp.pprint(save_query))
#                 if debug: print("END RdfClass.save ---------------------------\n")
#                 save_results.append(self._run_save_query(save_query))
#             consolidated = {}
#             object_values = []
#             for result in save_results:
#                 consolidated['status'] = result.get("status")
#                 object_values.append(result.get("lastSave",{}).get("objectValue"))
#             consolidated['lastSave'] = {"objectValue":",".join(object_values)}
#             return consolidated
#         else:
#             save_data = self._process_class_data(rdf_obj)
#             if debug: print("-------------- Save data:\n",pp.pprint(save_data))
#             save_query = self._generate_save_query(save_data)
#             if debug: print("save_query: \n", pp.pprint(save_query))
#             if debug: print("END RdfClass.save ---------------------------\n")
#             return self._run_save_query(save_query)
#         #return None

#     def new_uri(self, **kwargs):
#         ''' Generates a new uri for a new subject
        
#             kwargs:
#                 save_data - pass in the data to be saved for uri 
#                 calculations'''
                
#         if not DEBUG:
#             debug = False
#         else:
#             debug = False
#         if debug: print("START RdfClass.new_uri ---------------------------\n")
#         return_val = ''
#         if self.kds_saveLocation == "triplestore":
#             # get a uuid by saving an empty record to the repo and then
#             # delete the item.
#             if "!--uuid" in self.kdssubjectPattern:
#                 repository_result = requests.post(
#                                 self.repository_url,
#                                 data="",
#                 				headers={"Content-type": "text/turtle"})
#                 object_value = repository_result.text
#                 uid = re.sub(r'^(.*[#/])','',object_value)
#                 requests.delete(object_value)
#             else:
#                 uid = ''
#             if self.kds_storageType != "blanknode":
#                 if debug: print("new uid: ", uid)
#                 return_val = self.uri_patterner(uid, **kwargs)
#         return return_val
#         if debug: print("END RdfClass.new_uri ---------------------------\n")

#     def uri_patterner(self, uid, **kwargs):
#         if not DEBUG:
#             debug = False
#         else:
#             debug = True
#         if debug: print("START RdfClass.uri_patterner ---------------------\n")
#         pattern = kwargs.get("kdssubjectPattern", self.kdssubjectPattern)
#         pattern_args = pattern.split(",")
#         new_args = []
#         for arg in pattern_args:
#             if arg.startswith("!--"):
#                 if arg == "!--baseUrl":
#                     value = self.kds_baseUrl
#                 elif arg == "!--classPrefix":
#                     value = uri_prefix(self.kds_classUri).lower()
#                 elif arg == "!--className":
#                     value = nouri(self.kds_classUri)
#                 elif arg == "!--uuid":
#                     value = uid
#                 elif arg.startswith("!--slugify"):
#                     _prop_uri = arg[arg.find("(")+1:arg.find(")")]
#                     _prop_uri = pyuri(_prop_uri)
#                     data = kwargs.get('save_data',{}).get("data",[[]])
#                     _value_to_slug = ""
#                     for item in data:
#                         if item[0] == _prop_uri:
#                             _value_to_slug = \
#                                     item[1][1:item[1].find('"^^xsd')]
#                     if is_not_null(_value_to_slug):
#                         value = slugify(_value_to_slug)
#                 else:
#                     value = arg.replace("!--","")
#             else:
#                 value = arg
#             new_args.append(value)
#         new_uri = uri("".join(new_args))
#         if new_uri.startswith("http://"):
#             temp_uri = new_uri.replace("http://","").replace("//","/")
#             if temp_uri[:1] == "/":
#                 temp_uri = temp_uri[1:]
#             new_uri = "http://" + temp_uri
#         elif new_uri.startswith("https://"):
#             temp_uri = new_uri.replace("https://","").replace("//","/")
#             if temp_uri[:1] == "/":
#                 temp_uri = temp_uri[1:]
#             new_uri = "https://" + temp_uri
#         if debug: print("pattern: %s\nuid: %s\nnew_uri: %s" %
#                     (pattern, uid, new_uri))
#         # if the new_uri does not have a uid in it test for uniqueness
#         if not is_not_null(uid):
#             failed_test = True
#             i = 1
#             test_uri = new_uri
#             while failed_test:
#                 sparql = """
#                          SELECT * 
#                          WHERE {
#                             {%s ?p ?o} UNION {?s ?p %s}
#                          } LIMIT 1""" % (iri(test_uri), iri(test_uri))
#                 results = requests.post(self.triplestore_url,
#                                         data={"query": sparql, "format": "json"})
#                 if debug: print("new_uri_test: ", results.json())
#                 _uri_test = results.json().get('results').get( \
#                             'bindings', [])
#                 # if the length of the return is 0 the uri is unique
#                 if len(_uri_test) == 0:
#                     failed_test = False
#                 # if not add in incremented number to the end of the uri
#                 else:
#                     test_uri = "%s_%s" % (new_uri, i)
#                     i += 1
#             new_uri = test_uri
#         if debug: print("END RdfClass.uri_patterner -----------------------\n")
#         return new_uri

#     def validate_obj_data(self, rdf_obj, old_data):
#         '''This method will validate whether the supplied object data
#            meets the class requirements and returns the results'''
#         _validation_steps = {}
#         _validation_steps['validRequiredFields'] = \
#                 self._validate_required_properties(rdf_obj, old_data)
#         _validation_steps['validPrimaryKey'] = \
#                 self.validate_primary_key(rdf_obj, old_data)
#         _validation_steps['validFieldData'] = \
#                 self._validate_property_data(rdf_obj, old_data)
#         _validation_steps['validSecurity'] =  \
#                 self._validate_security(rdf_obj, old_data)
#         #print("----------------- Validation ----------------------\n", \
#                 #json.dumps(_validation_steps, indent=4))
#         _validation_errors = []
#         for step in _validation_steps:
#             if _validation_steps[step][0] != "valid":
#                 for _error in _validation_steps[step]:
#                     _validation_errors.append(_error)
#         if len(_validation_errors) > 0:
#             return {"success": False, "errors":_validation_errors}
#         else:
#             return {"success": True}

#     def validate_primary_key(self, rdf_obj, old_data):
#         '''query to see if PrimaryKey is Valid'''
#         if not DEBUG:
#             debug = False
#         else:
#             debug = True
#         if debug: print("START RdfClass.validate_primary_key --------------\n")
#         if debug: print("old_data:\n",json.dumps(old_data,indent=4))
#         if old_data is None:
#             old_data = {}
#         _prop_name_list = []
#         if hasattr(self, "kds_primaryKey"):
#             pkey = self.kds_primaryKey
#             if isinstance(pkey, dict):
#                 pkey = pkey.get("kds_keyCombo",[])
#             pkey = make_list(pkey)
#         else:
#             pkey = []
#         if debug: print(self.kds_classUri, " PrimaryKeys: ", pkey, "\n")
#         if len(pkey) < 1:
#             if debug: print("END RdfClass.validate_primary_key -NO pKey----\n")
#             return ["valid"] 
#         else:
#             _calculated_props = self._get_calculated_properties()
#             _old_class_data = self._select_class_query_data(old_data)
#             _new_class_data = {}
#             _query_args = [make_triple("?uri", "a", \
#                     iri(uri(self.kds_classUri)))]
#             _multi_key_query_args = copy.deepcopy(_query_args)
#             _key_changed = False
#             _prop_uri_list = []
#             _key_props = []
#             # get primary key data from the form data
#             for prop in rdf_obj:
#                 if prop.kds_propUri in pkey:
#                     _new_class_data[prop.kds_propUri] = prop.data
#                     _prop_name_list.append(prop.kds_formLabelName)
#                     _key_props.append(prop)

#             for key in pkey:
#                 _object_val = None
#                 #get the _data_value to test against
#                 _data_value = _new_class_data.get(key, _old_class_data.get(key))
#                 if is_not_null(_data_value):
#                     _range_obj = make_list(self.kds_properties[key].get(\
#                             "rdfs_range", [{}]))[0]
#                     _data_type = _range_obj.get('storageType')
#                     _range = _range_obj.get('rangeClass')
#                     if debug: print("_data_type: ", _data_type)
#                     if _data_type == 'literal':
#                         _object_val = "FILTER regex(str(?o), %s, 'i') " % \
#                             json.dumps(_data_value)
#                         #RdfDataType(_range).sparql(_data_value)
#                     else:
#                         _object_val = iri(uri(_data_value))
#                 else:
#                     # if data is missing from the key fields exit method and
#                     # return valid. *** The object value does not exist and
#                     #                   will be generated when another class
#                     #                   is saved
#                     if debug: print(\
#                         "END RdfClass.validate_primary_key - NO data-------\n")
#                     return ["valid"]
#                 # if the old_data is not equel to the newData re-evaluate
#                 # the primaryKey

#                 # if the old value is not equal to the new value need to test
#                 # the key
#                 # if the new value is to be calculated, i.e. a dependant class
#                 # generating a value then we don't need to test the key.
#                 # however if there is a supplied value and it is listed as a
#                 # calculated property we need to test.
#                 if debug: print("old: %s\nNew: %s\nKey: %s\nCalc_props: %s" % \
#                         (_old_class_data.get(key),
#                          _new_class_data.get(key),
#                          key,
#                          _calculated_props))    
#                 if (_old_class_data.get(key) != _new_class_data.get(key)) and \
#                         ((key not in _calculated_props) or \
#                         _new_class_data.get(key) is not None):
                    
#                     _key_changed = True
#                     if _object_val:
#                         if str(_object_val).startswith("FILTER"):
#                             arg_trip = make_triple("?uri", iri(uri(key)), "?o")
#                             _query_args.append(arg_trip)
#                             _query_args.append("FILTER (!(isIri(?o))) .")
#                             _query_args.append(_object_val) 
#                             _multi_key_query_args.append(arg_trip)
#                             _multi_key_query_args.append(\
#                                     "FILTER (!(isIri(?o))) .")
#                             _multi_key_query_args.append(_object_val) 
#                         else:    
#                             _query_args.append(make_triple("?uri", 
#                                                            iri(uri(key)), \
#                                                            _object_val))    
#                             _multi_key_query_args.append(make_triple("?uri", \
#                                     iri(uri(key)), _object_val))
#                 else:
#                     if _object_val:
#                         _multi_key_query_args.append(make_triple("?uri", \
#                                 iri(uri(key)), _object_val))
#                     else:
#                         _key_changed = False
#             # if the primary key changed in the form we need to
#             # query to see if there is a violation with the new value

#             if _key_changed:
#                 if len(pkey) > 1:
#                     args = _multi_key_query_args
#                 else:
#                     args = _query_args
#                 sparql = '''
#                          {}\nSELECT DISTINCT (COUNT(?uri)>0 AS ?keyViolation)
#                          {{\n{}\n}}\nGROUP BY ?uri'''.format(\
#                                 rdfw().get_prefix(),
#                                 "\n".join(args))
#                 if debug: print("----------- PrimaryKey query:\n", sparql)
#                 _key_test_results =\
#                         requests.post(\
#                                 self.triplestore_url,
#                                 data={"query": sparql, "format": "json"})
#                 if debug: print("_key_test_results: ", _key_test_results.json())
#                 _key_test = _key_test_results.json().get('results').get( \
#                         'bindings', [])
#                 if debug: print(_key_test)
#                 if len(_key_test) > 0:
#                     _key_test = _key_test[0].get('keyViolation', {}).get( \
#                             'value', False)
#                 else:
#                     _key_test = False


#                 if not _key_test:
#                     if debug: print(\
#                         "END RdfClass.validate_primary_key - Key Passed --\n")
#                     return ["valid"]
#                 else:
#                     error_msg = "This {} aleady exists.".format(
#                                         " / ".join(_prop_name_list))
#                     for prop in _key_props:
#                         if hasattr(prop, "errors"):
#                             if isinstance(prop.errors, list):
#                                 prop.errors.append(error_msg)
#                             else:
#                                 prop.errors = [error_msg]
#                         else:
#                             setattr(prop, "errors", [error_msg])
#                     return [{"errorType":"primaryKeyViolation",
#                              "formErrorMessage": error_msg,
#                              "errorData":{"class": self.kds_classUri,
#                                           "propUri": pkey}}]
#             if debug: print(\
#                 "START RdfClass.validate_primary_key - Skipped Everything--\n")
#             return ["valid"]

#     def list_required(self):
#         '''Returns a set of the required properties for the class'''
#         _required_list = set()
#         for _prop, _value in self.kds_properties.items():
#             if _value.get('kds_requiredByDomain') == self.kds_classUri:
#                 _required_list.add(_prop)
#         try:
#             if isinstance(self.primaryKey, list):
#                 for key in self.primaryKey:
#                     _required_list.add(key)
#             else:
#                 _required_list.add(self.primaryKey)
#         except:
#             pass
#         return _required_list

#     def list_properties(self):
#         '''Returns a set of the properties used for the class'''
#         property_list = set()
#         for p in self.kds_properties:
#             property_list.add(self.kds_properties[p].get('propUri'))
#         return property_list

#     def list_dependant(self):
#         '''Returns a set of properties that are dependent upon the
#         creation of another object'''
#         _dependent_list = set()
#         for _prop in self.kds_properties:
#             _range_list = make_list(self.kds_properties[_prop].get('rdfs_range'))
#             for _row in _range_list:
#                 if _row.get('storageType') == "object" or \
#                         _row.get('storageType') == "blanknode":
#                     _dependent_list.add(_prop)
#         _return_obj = []
#         for _dep in _dependent_list:
#             _range_list = make_list(self.kds_properties[_dep].get('rdfs_range'))
#             for _row in _range_list:
#                 if _row.get('storageType') == "object" or \
#                    _row.get('storageType') == "blanknode":
#                     _return_obj.append(
#                         {"kds_propUri": self.kds_properties[_dep].get("kds_propUri"),
#                          "kds_classUri": _row.get("rangeClass")})
#         return _return_obj

#     def get_property(self, prop_uri):
#         '''Method returns the property json object

#         keyword Args:
#             prop_name: The Name of the property
#             prop_uri: The URI of the property
#             ** the PropName or URI is required'''
#         try:
#             return self.kds_properties.get(prop_uri)
#         except:
#             return None

#     def _validate_required_properties(self, rdf_obj, old_data):
#         '''Validates whether all required properties have been supplied and
#             contain data '''
#         debug = False
#         _return_error = []
#         #create sets for evaluating requiredFields
#         _required = self.list_required()
#         if debug: print("Required Props: ", _required)
#         _data_props = set()
#         _deleted_props = set()
#         for prop in rdf_obj:
#             #remove empty data properties from consideration
#             if debug: print(prop,"\n")
#             if is_not_null(prop.data) or prop.data != 'None':
#                 _data_props.add(prop.kds_propUri)
#             else:
#                 _deleted_props.add(prop.kds_propUri)
#         # find the properties that already exist in the saved class data
#         _old_class_data = self._select_class_query_data(old_data)
#         for _prop in _old_class_data:
#             # remove empty data properties from consideration
#             if is_not_null(_old_class_data[_prop]) or _old_class_data[_prop]\
#                     != 'None':
#                 _data_props.add(_prop)
#         # remove the _deleted_props from consideration and add calculated props
#         _valid_props = (_data_props - _deleted_props).union( \
#                 self._get_calculated_properties())
#         #Test to see if all the required properties are supplied
#         missing_required_properties = _required - _valid_props
#         if len(missing_required_properties) > 0:
#             _return_error.append({
#                 "errorType":"missing_required_properties",
#                 "errorData":{
#                     "class":self.kds_classUri,
#                     "properties":make_list(missing_required_properties)}})
#         if len(_return_error) > 0:
#             _return_val = _return_error
#         else:
#             _return_val = ["valid"]
#         return _return_val

#     def _get_calculated_properties(self):
#         '''lists the properties that will be calculated if no value is
#            supplied'''
#         _calc_list = set()
#         # get the list of processors that will calculate a value for a property
#         _value_processors = rdfw().value_processors
#         for _prop in self.kds_properties:
#             # Any properties that have a default value will be generated at
#             # time of save
#             if is_not_null(self.kds_properties[_prop].get('kds_defaultVal')):
#                 _calc_list.add(self.kds_properties[_prop].get('kds_propUri'))
#             # get the processors that will run on the property
#             _processors = make_list(self.kds_properties[_prop].get(\
#                     'kds_propertyProcessing', []))
#             # find the processors that will generate a value
#             for _processor in _processors:
#                 #print("processor: ", processor)
#                 if _processor.get("rdf_type") in _value_processors:
#                     _calc_list.add(_prop)
#         #any dependant properties will be generated at time of save
#         _dependent_list = self.list_dependant()
#         # properties that are dependant on another class will assume to be
#         # calculated
#         for _prop in _dependent_list:
#             _calc_list.add(_prop.get("kds_propUri"))
#         return remove_null(_calc_list)

#     def _validate_dependant_props(self, rdf_obj, old_data):
#         '''Validates that all supplied dependant properties have a uri as an
#             object'''
#         # dep = self.list_dependant()
#         # _return_error = []
#         _data_props = set()
#         for _prop in rdf_obj:
#             #remove empty data properties from consideration
#             if is_not_null(_prop.data):
#                 _data_props.add(_prop.kds_propUri)
#         '''for p in dep:
#             _data_value = data.get(p)
#             if (is_not_null(_data_value)):
#                 propDetails = self.kds_properties[p]
#                 r = propDetails.get('range')
#                 literalOk = false
#                 for i in r:
#                     if i.get('storageType')=='literal':
#                         literalOk = True
#                 if not is_valid_object(_data_value) and not literalOk:
#                     _return_error.append({
#                         "errorType":"missingDependantObject",
#                         "errorData":{
#                             "class":self.kds_classUri,
#                             "properties":propDetails.get('propUri')}})
#         if len(_return_error) > 0:
#             return _return_error
#         else:'''
#         return ["valid"]

#     def _validate_property_data(self, rdf_obj, old_data):
#         return ["valid"]

#     def _validate_security(self, rdf_obj, old_data):
#         return ["valid"]

#     def _process_class_data(self, rdf_obj, **kwargs):
#         '''Reads through the processors in the defination and processes the
#             data for saving'''
#         if not DEBUG:
#             debug = False
#         else:
#             debug = True
#         if debug: print("START rdfclass.RdfClass._process_class_data ------\n")
#         _pre_save_data = {}
#         _save_data = {}
#         _processed_data = {}
#         obj = {}
#         _required_props = self.list_required()
        
#         _calculated_props = self._get_calculated_properties()
#         _old_data = self._select_class_query_data(rdf_obj.query_data)
#         # cycle through the form class data and add old, new, doNotSave and
#         # processors for each property
#         if kwargs.get("class_props"):
#             _class_obj_props = kwargs.get("class_props")
#         else:
#             _class_obj_props = rdf_obj.class_grouping.get(self.kds_classUri,[])
#         subject_uri = "<>"
#         for prop in _class_obj_props:
#             if hasattr(prop, "subject_uri"):
#                 if prop.subject_uri is not None:
#                     subject_uri = prop.subject_uri
#                     break
#         subject_uri = _old_data.get("!!!!subjectUri", "<>")
#         for prop in _class_obj_props:
#             '''if debug: print("prop dict ----------------------\n",
#                             pp.pprint(prop.__dict__),
#                             "\n---------------------\n")'''
#             _prop_uri = prop.kds_propUri
#             if debug:
#                 if _prop_uri == "schema_image":
#                     x=1
#             # gather all of the processors for the property
#             _class_prop = self.kds_properties.get(_prop_uri,{})
#             _class_prop_processors = make_list(_class_prop.get("kds_propertyProcessing"))
#             _form_prop_processors = make_list(prop.kds_processors)
#             # clean the list of processors by sending a list based on
#             # precedence i.e. the form processors should override the rdf_class
#             # processors
#             processors = clean_processors([_form_prop_processors,
#                                            _class_prop_processors],
#                                            self.kds_classUri)
#             # remove the property from the list of required properties
#             # required properties not in the form will need to be addressed
#             _required_prop = False
#             if _prop_uri in _required_props:
#                 _required_props.remove(_prop_uri)
#                 _required_prop = True
#             # remove the property from the list of calculated properties
#             # calculated properties not in the form will need to be addressed
#             if _prop_uri in _calculated_props:
#                 _calculated_props.remove(_prop_uri)
#             # add the information to the _pre_save_data object
#             if not _pre_save_data.get(_prop_uri):
#                 _pre_save_data[_prop_uri] =\
#                         {"new":prop.data,
#                          "old":prop.old_data,
#                          "classUri": prop.kds_classUri,
#                          "required": _required_prop,
#                          "editable": prop.editable,
#                          "doNotSave": prop.doNotSave,
#                          "processors": processors}
#             else:
#                 _temp_list = make_list(_pre_save_data[_prop_uri])
#                 _temp_list.append(\
#                         {"new":prop.data,
#                          "old":prop.old_data,
#                          "classUri": prop.kds_classUri,
#                          "required": _required_prop,
#                          "editable": prop.editable,
#                          "doNotSave": prop.doNotSave,
#                          "processors": processors})
#                 _pre_save_data[_prop_uri] = _temp_list
#         # now deal with missing required properties. cycle through the
#         # remaing properties and add them to the _pre_save_data object
#         for _prop_uri in _required_props:
#             _class_prop = self.kds_properties.get(_prop_uri,{})
#             _class_prop_processors = clean_processors([make_list(\
#                             _class_prop.get("kds_propertyProcessing"))],
#                             self.kds_classUri)
#             if _prop_uri == "schema_alternativeName":
#                 x=1
#             # remove the prop from the remaining calculated props
#             if _prop_uri in _calculated_props:
#                 _calculated_props.remove(_prop_uri)
#             if not _pre_save_data.get(_prop_uri):
#                 _pre_save_data[_prop_uri] =\
#                         {"new":NotInFormClass(),
#                          "old":_old_data.get(_prop_uri),
#                          "doNotSave":False,
#                          "classUri": self.kds_classUri,
#                          "required": True,
#                          "editable": True,
#                          "processors":_class_prop_processors,
#                          "defaultVal":_class_prop.get("kds_defaultVal")}
#                 if debug: print("psave: ", _pre_save_data[_prop_uri])
#             else:
#                 _temp_list = make_list(_pre_save_data[_prop_uri])
#                 _pre_save_data[_prop_uri] = _temp_list.append(\
#                         {"new":NotInFormClass(),
#                          "old":_old_data.get(_prop_uri),
#                          "doNotSave": False,
#                          "classUri": self.kds_classUri,
#                          "editable": True,
#                          "processors":_class_prop_processors,
#                          "defaultVal":_class_prop.get("kds_defaultVal")})

#         # now deal with missing calculated properties. cycle through the
#         # remaing properties and add them to the _pre_save_data object
#         if debug: print("calc props: ", _calculated_props)
#         for _prop_uri in _calculated_props:
#             if debug: print("########### _calculated_props: ")
#             _class_prop = self.kds_properties.get(_prop_uri,{})
#             _class_prop_processors = clean_processors([make_list(\
#                     _class_prop.get("kds_propertyProcessing"))],
#                     self.kds_classUri)
#             if not _pre_save_data.get(_prop_uri):
#                 _pre_save_data[_prop_uri] =\
#                         {"new":NotInFormClass(),
#                          "old":_old_data.get(_prop_uri),
#                          "doNotSave":False,
#                          "processors":_class_prop_processors,
#                          "defaultVal":_class_prop.get("kds_defaultVal")}
#             else:
#                 _temp_list = make_list(_pre_save_data[_prop_uri])
#                 _pre_save_data[_prop_uri] =\
#                         _temp_list.append(\
#                                 {"new":NotInFormClass(),
#                                  "old":_old_data.get(_prop_uri),
#                                  "doNotSave":False,
#                                  "processors":_class_prop_processors,
#                                  "defaultVal":_class_prop.get("kds_defaultVal")})
#         # cycle through the consolidated list of _pre_save_data to
#         # test the security, run the processors and calculate any values
#         for _prop_uri, prop in _pre_save_data.items():
#             # ******* doNotSave property is set during form field creation
#             # in get_wtform_field method. It tags fields that are there for
#             # validation purposes i.e. password confirm fields ******

#             if isinstance(prop, list):
#                 # a list with in the property occurs when there are
#                 # multiple fields tied to the property. i.e.
#                 # password creation or change / imagefield that
#                 # takes a URL or file
#                 for _prop_instance in prop:
#                     if _prop_instance.get("doNotSave", False):
#                         _pre_save_data[_prop_uri].remove(_prop_instance)
#                 if len(make_list(_pre_save_data[_prop_uri])) == 1:
#                     _pre_save_data[_prop_uri] = _pre_save_data[_prop_uri][0]
#             # doNotSave = prop.get("doNotSave", False)
#         for _prop_uri, _prop in _pre_save_data.items():
#             # send each property to be proccessed
#             if _prop:
#                 obj = self._process_prop({"propUri":_prop_uri,
#                                           "prop": _prop,
#                                           "processedData": _processed_data,
#                                           "preSaveData": _pre_save_data})
#                 _processed_data = obj["processedData"]
#                 _pre_save_data = obj["preSaveData"]
#         if debug: print("PreSaveData----------------")
#         if debug: print(json.dumps(dumpable_obj(_pre_save_data), indent=4))
#         _save_data = {"data":self.__format_data_for_save(_processed_data,
#                                                          _pre_save_data),
#                       "subjectUri":subject_uri}
#         return _save_data

#     def _generate_save_query(self, save_data_obj, subject_uri=None):
#         if not DEBUG:
#             debug = False
#         else:
#             debug = True
#         if debug: print("START RdfClass._generate_save_query -------------\n")
#         _save_data = save_data_obj.get("data")
#         # find the subject_uri positional argument or look in the save_data_obj
#         # or return <> as a new node
#         if not subject_uri:
#             subject_uri = iri(uri(save_data_obj.get('subjectUri', "<>")))
#         _save_type = self.kds_storageType
#         if subject_uri == "<>" and _save_type.lower() == "blanknode":
#             _save_type = "blanknode"
#         else:
#             _save_type = "object"
#         new_status = False
#         if self.kds_saveLocation == "triplestore" and subject_uri == "<>":
#             subject_uri = iri(self.new_uri(save_data=save_data_obj))
#             new_status = True
#         _bn_insert_clause = []
#         _insert_clause = ""
#         _delete_clause = ""
#         _where_clause = ""
#         _prop_set = set()
#         i = 1
#         j = 1000
#         if debug: print("save data in generateSaveQuery\n", \
#                     pp.pprint(_save_data))
#         # test to see if there is data to save
#         if len(_save_data) > 0:
#             for prop in _save_data:
#                 # test to see if the object value is a blank node
#                 if isinstance(prop[1], str) and prop[1][:1] == "[":
#                     # build the blanknode linkage
#                     prop_range_list = get_attr(self, pyuri(_prop_uri))['rdfs_range']
#                     for rng in make_list(prop_range_list):
#                         if rng.get("storageType") == "blanknode":
#                             prop_range = rng.get("rangeClass")
#                     linked_prop = uri(get_attr(rdfw(),prop_range).kds_blankNodeLink)
#                     line1 = make_triple(subject_uri, _prop_uri, "?" + str(j))
#                     line2 = make_triple("?" + str(j), iri(uri(linked_prop)))
#                     #_bn_delete_clause.append(
#                 _prop_set.add(uri(prop[0]))
#                 _prop_iri = iri(uri(prop[0]))
#                 if not isinstance(prop[1], DeleteProperty):
#                     _obj_val = uri(prop[1])
#                     _insert_clause += "{}\n".format(\
#                                         make_triple(subject_uri, _prop_iri, _obj_val))
#                     _bn_insert_clause.append("\t{} {}".format(_prop_iri, _obj_val))
#             if subject_uri != '<>' and not new_status:
#                 for prop in _prop_set:
#                     _prop_iri = iri(uri(prop))
#                     _delete_clause += "{}\n".format(\
#                                     make_triple(subject_uri, _prop_iri, "?"+str(i)))
#                     _where_clause += "OPTIONAL {{ {} }} .\n".format(\
#                                     make_triple(subject_uri, _prop_iri, "?"+str(i)))
#                     i += 1
#             else:
#                 _obj_val = iri(uri(self.kds_classUri))
#                 _insert_clause += make_triple(subject_uri, "a", _obj_val) + \
#                         "\n"
#                 _bn_insert_clause.append("\t a {}".format(_obj_val))
#             if _save_type == "blanknode":
#                 _save_query = "[\n{}\n]".format(";\n".join(_bn_insert_clause))
#             else:
#                 if subject_uri != '<>' and not new_status:
#                     save_query_template = Template("""{{ prefix }}
#                                     DELETE \n{
#                                     {{ _delete_clause }} }
#                                     INSERT \n{
#                                     {{ _insert_clause }} }
#                                     WHERE \n{
#                                     {{ _where_clause }} }""")
#                     _save_query = save_query_template.render(
#                         prefix=rdfw().get_prefix(),
#                         _delete_clause=_delete_clause,
#                         _insert_clause=_insert_clause,
#                         _where_clause=_where_clause)
#                 else:
#                     _save_query = "{}\n\n{}".format(
#                         rdfw().get_prefix("turtle"),
#                         _insert_clause)
#             if debug: print(_save_query)
#             if debug: print("END RdfClass._generate_save_query -------------\n")
#             return {"query":_save_query, "subjectUri":subject_uri,
#                     "new_status":new_status}
#         else:
#             if debug: print("END RdfClass._generate_save_query -------------\n")
#             return {"subjectUri":subject_uri}

#     def _run_save_query(self, save_query_obj, subject_uri=None):
#         if not DEBUG:
#             debug = False
#         else:
#             debug = False
#         _save_query = save_query_obj.get("query")
#         if debug: print("START RdfClass._run_save_query -------------------\n")
#         if debug: print("triplestore: ", self.triplestore_url)
#         if debug: print("repository: ", self.repository_url)
#         if not subject_uri:
#             subject_uri = save_query_obj.get("subjectUri")
#         if debug: print("_save_query:\n", _save_query)
#         if _save_query:
#             # a "[" at the start of the save query denotes a blanknode
#             # return the blanknode as the query result
#             if _save_query[:1] == "[":
#                 object_value = _save_query
#             else:
#                 # if there is no subject_uri create a new entry in the
#                 # repository
#                 if subject_uri == "<>" or save_query_obj.get("new_status"):
#                     if debug: print("Enter New")
#                     if self.kds_saveLocation == "repository":
#                         repository_result = requests.post(
#                                 self.repository_url,
#                                 data=_save_query,
#                                 headers={"Content-type": "text/turtle"})
#                         if debug: print("repository_result: ",
#             	                        repository_result,
#             	                        " ",
#             	                        repository_result.text)
#                         object_value = repository_result.text
#                     elif self.kds_saveLocation == "triplestore":
#                         triplestore_result = requests.post(
#                                 url=self.triplestore_url,
#                                 headers={"Content-Type":
#                                          "text/turtle"},
#                                 data=_save_query)
#                         if debug: print("triplestore_result: ",
#                                         triplestore_result,
#                                         " ",
#                                         triplestore_result.text)
#                         object_value = subject_uri
#                     elif self.kds_saveLocation == "elasticsearch":
#                             print ("**************** ES Connection NOT Built")
#                     elif self.kds_saveLocation == "sql_database":
#                             print ("**************** SQL Connection NOT Built")
#                 # if the subject uri exists send an update query to the
#                 # specified datastore
#                 else:
#                     if debug: print("Enter Update")
#                     if self.kds_saveLocation == "repository":
#                         _headers = {"Content-type":
#                                     "application/sparql-update"}
#                         _url = clean_iri(subject_uri)
#                         repository_result = \
#                                 requests.patch(_url, data=_save_query,
#             				                   headers=_headers)
#                         if debug: print("repository_result: ",
#             	                        repository_result,
#             	                        " ",
#             	                        repository_result.text)
#                         object_value = iri(subject_uri)
#                     elif self.kds_saveLocation == "triplestore":
#                         _url = self.triplestore_url
#                         triplestore_result = requests.post(_url,
#                                 data={"update":_save_query})
#                         if debug: print("triplestore_result: ",
#                                         triplestore_result,
#                                         " ",
#                                         triplestore_result.text)
#                         object_value = iri(subject_uri)
#                     elif self.kds_saveLocation == "elasticsearch":
#                         print ("**************** ES Connection NOT Built")
#                     elif self.kds_saveLocation == "sql_database":
#                         print ("**************** SQL Connection NOT Built")
#             if debug: print("END RdfClass._run_save_query ----------------\n")
#             return {"status": "success",
#                     "lastSave": {
#                         "objectValue": object_value}
#                    }
#         else:
#             if debug: print("Enter No Data to Save")
#             if debug: print("END RdfClass._run_save_query ---NO DATA-------\n")
#             return {"status": "success",
#                     "lastSave": {
#                         "objectValue": iri(subject_uri),
#                         "comment": "No data to Save"}
#                    }

#     def _process_prop(self, obj):
#         # obj = propUri, prop, processedData, _pre_save_data
#         # !!!!!!! the merge_prop function will need to be relooked for
#         # instances where we have multiple property entries i.e. a fieldList
#         if not DEBUG:
#             debug = False
#         else:
#             debug = False
#         if debug: print("START RdfClass._process_prop -------------------\n")
#         if len(make_list(obj['prop'])) > 1:
#             obj = self.__merge_prop(obj)
#         processors = obj['prop'].get("processors", [])
#         _prop_uri = obj['propUri']
#         # process properties that are not in the form
#         if isinstance(obj['prop'].get("new"), NotInFormClass) and \
#                 not is_not_null(obj['prop'].get("old")):
#             # process required properties
#             if obj['prop'].get("required"):
#                 # run all processors: the processor determines how to
#                 # handle if there is old data
#                 if len(processors) > 0:
#                     for processor in processors.values():
#                         obj = run_processor(processor, obj)
#                 # if the processors did not calculate a value for the
#                 # property attempt to calculte from the default
#                 # property settings
#                 if not obj['prop'].get('calcValue', False):
#                     obj_value = calculate_default_value(obj['prop'])
#                     obj['processedData'][obj['propUri']] = obj_value
#             #else:
#                 # need to decide if you want to calculate properties
#                 # that are not required and not in the form
#         # if the property is editable process the data
#         elif obj['prop'].get("editable"):
#             # if the old and new data are different
#             if clean_iri(obj['prop'].get("new")) != \
#                                     clean_iri(obj['prop'].get("old")):
#                 # if the new data is null and the property is not
#                 # required run the processors first then mark property for
#                 # deletion if it is still should be deleted
#                 if not is_not_null(obj['prop'].get("new")) and not \
#                                                 obj['prop'].get("required"):
#                     for processor in processors.values():
#                             obj = run_processor(processor, obj)
#                     if not obj['prop']['doNotSave']:
#                         obj['processedData'][_prop_uri] = DeleteProperty()
#                 # if the property has new data
#                 elif is_not_null(obj['prop'].get("new")):
#                     if len(processors) > 0:
#                         for processor in processors.values():
#                             obj = run_processor(processor, obj)
#                         if not obj['prop'].get('calcValue', False):
#                             obj['processedData'][_prop_uri] = \
#                                                        obj['prop'].get("new")
#                     else:
#                         obj['processedData'][_prop_uri] = obj['prop'].get("new")
#         if debug: print("END RdfClass._process_prop -------------------\n")
#         return obj

#     def __calculate_property(self, obj):
#         ''' Reads the obj and calculates a value for the property'''
#         return obj

#     def __merge_prop(self, obj):
#         '''This will need to be expanded to handle more cases right now
#         the only case is an image '''
#         #_prop_list = obj['prop']
#         _keep_image = -1

#         for i, prop in enumerate(obj['prop']):
#             if isinstance(prop['new'], FileStorage):
#                 if prop['new'].filename:
#                     _keep_image = i
#                     break
#         for i, prop in enumerate(obj['prop']):
#             if i != _keep_image:
#                 obj['prop'].remove(prop)
#         obj['prop'] = obj['prop'][0]
#         return obj
#         '''_prop_list = obj['prop']
#         _class_prop = self.get_property(prop_uri=obj['propUri'])
#         propRange = _class_prop.get('''
#         '''for prop in _prop_list:
#             for name, attribute in prop.items():
#                 if conflictingValues.get(name):
#                     if isinstance(conflictingValues.get(name), list):
#                         if not attribute in conflictingValues.get(name):
#                             conflictingValues[name].append(attribute)
#                     elif conflictingValues.get(name) != attribute:
#                         conflictingValues[name] = [conflictingValues[name],
#                                                    attribute]
#                 else:
#                     conflictingValues[name] = attribute'''

#     def __format_data_for_save(self, processed_data, pre_save_data):
#         ''' takes the processed data and formats the values for the sparql
#             query '''
#         if not DEBUG:
#             debug = False
#         else:
#             debug = True
#         if debug: print("START RdfClass.__format_data_for_save -----------\n")
#         _save_data = []
#         #if "obi_recipient" in pre_save_data.keys():
#         #    x=y
#         if debug: print("format data***********\n")
#         if debug: pp.pprint(processed_data)
#         if not processed_data:
#             processed_data = {}
#         # cycle throught the properties in the processed data
#         for _prop_uri, prop in processed_data.items():
#             # if the property is maked for deletion add it to the save list
#             if isinstance(prop, NotInFormClass):
#                 pass
#             elif isinstance(prop, DeleteProperty):
#                 _save_data.append([_prop_uri, prop])
#             # if the property is a file object send it to the repository and
#             # add the new uri to the save data list
#             elif isinstance(prop, FileStorage):
#                 _file_iri = save_file_to_repository(\
#                         prop, pre_save_data[_prop_uri][0].get('old'))
#                 _save_data.append([_prop_uri, _file_iri])
#             # otherwise determine the range of the property and format it in
#             # the correct sparl format
#             else:
#                 # some properties have more than one option for the object
#                 # value i.e. schema:image can either store a ImageObject or
#                 # a Url to an image. We need to determine the range options
#                 _range_list = make_list(self.kds_properties[_prop_uri].get(\
#                         "rdfs_range", [{}]))
#                 _storage_types = set()
#                 _data_types = set()
#                 # cycle through the range_list and get the sets of options
#                 for _range_dict in _range_list:
#                     _storage_types.add(_range_dict.get('storageType'))
#                     if _range_dict.get('storageType') == "literal":
#                         _data_types.add(_range_dict.get('rangeClass'))
#                 _data_type = "xsd_string"
#                 for _type in _data_types:
#                     if "xsd" in _type:
#                         _data_type = _type
#                 # cycle through the items in the current prop
#                 _value_list = make_list(prop)
#                 for item in _value_list:
#                     if 'object' in _storage_types or 'blanknode' in \
#                             _storage_types:
#                         uri_test = uri(item)
#                         if debug: print(_prop_uri, " - ", uri_test)
#                         if uri_test.startswith("http"):
#                             _save_data.append([_prop_uri, iri(uri(item))])
#                         elif 'literal' in _storage_types:
#                             _save_data.append([_prop_uri, RdfDataType(\
#                                     _data_type).sparql(str(item))])
#                         else:
#                             _save_data.append([_prop_uri, iri(uri(item))])
#                     else:
#                         _item = str(item).encode('unicode_escape')
#                         _save_data.append([_prop_uri, RdfDataType(\
#                                 _data_type).sparql(str(item))])
#         if debug: print("END RdfClass.__format_data_for_save -----------\n")
#         return _save_data

#     def _select_class_query_data(self, old_data):
#         ''' Find the data in query data that pertains to this class instance
#             returns dictionary of data with the subject_uri stored as
#             !!!!subject'''

#         #print("__________ class queryData:\n", \
#         #                        json.dumps(dumpable_obj(old_data), indent=4))
#         _old_class_data = {}
#         if old_data:
#             # find the current class data from the query
#             if isinstance(old_data, list):
#                 for entry in old_data:
#                     for subject_uri, value in entry.items():
#                         _class_types = make_list(value.get("rdf_type", []))
#                         for _rdf_type in _class_types:
#                             if _rdf_type == self.kds_classUri or \
#                                     _rdf_type == "<%s>" % self.kds_classUri:
#                                 _old_class_data = value
#                                 _old_class_data["!!!!subjectUri"] = subject_uri
#                                 break
#             else:
#                 for subject_uri in old_data:
#                     _class_types = make_list(old_data[subject_uri].get( \
#                         "rdf_type", []))
#                     for _rdf_type in _class_types:
#                         if _rdf_type == self.kds_classUri or \
#                                     _rdf_type == "<%s>" % self.kds_classUri:
#                             _old_class_data = old_data[subject_uri]
#                             _old_class_data["!!!!subjectUri"] = subject_uri
#                         break

#         return _old_class_data
