""" rdfframework module for generating rdfproperties. """
import pdb
import types
# pdb.set_trace()
# import rdfframework.rdfclass as rdfclass
from rdfframework.utilities import (find_values,
                                    make_doc_string,
                                    LABEL_FIELDS,
                                    RANGE_FIELDS,
                                    DESCRIPTION_FIELDS,
                                    DOMAIN_FIELDS,
                                    RegistryDictionary,
                                    pick,
                                    print_doc)
from rdfframework.datatypes import BaseRdfDataType, Uri, BlankNode, \
        RdfNsManager
from rdfframework.processors import PropertyProcessor
from rdfframework.configuration import RdfConfigManager
from rdfframework.rdfclass.esconversion import (convert_value_to_es,
                                                range_is_obj,
                                                get_prop_range_defs,
                                                get_prop_range_def,
                                                es_idx_types,
                                                get_idx_types)

__author__ = "Mike Stabile, Jeremy Nelson"

CFG = RdfConfigManager()
NSM = RdfNsManager()
MODULE = __import__(__name__)
domain_props = {}

properties = RegistryDictionary()

class RdfPropertyMeta(type):
    """ Metaclass for generating rdfproperty classes """

    @property
    def doc(cls):
        """ Prints the docstring for the class."""
        print_doc(cls)

    @classmethod
    def __prepare__(mcs, name, bases, **kwargs):
        # print('  RdfClassMeta.__prepare__(\n\t\t%s)' % (p_args(args, kwargs)))
        # if name == 'bf_hasItem':
        #     pdb.set_trace()
        prop_defs = kwargs.pop('prop_defs')
        prop_name = kwargs.pop('prop_name')
        cls_names = kwargs.pop('class_names')
        hierarchy = kwargs.pop('hierarchy')
        try:
            cls_names.remove('RdfClassBase')
        except ValueError:
            pass
        if not cls_names:
            return {}
        doc_string = make_doc_string(name,
                                     prop_defs,
                                     bases,
                                     None)
        new_def = prepare_prop_defs(prop_defs, prop_name, cls_names)
        new_def = filter_prop_defs(prop_defs, hierarchy, cls_names)
        new_def['__doc__'] = doc_string
        new_def['doc'] = property(print_doc)
        new_def['class_names'] = cls_names
        new_def['_prop_name'] = prop_name
        if prop_name == 'rdf_type':
            new_def['append'] = unique_append
        new_def['_init_processors'] = get_processors('kds_initProcessor',
                                                     prop_defs)
        new_def['_es_processors'] = get_processors('kds_esProcessor',
                                                   prop_defs,
                                                   'es_values')
        # pdb.set_trace()
        return new_def
        # x = super().__prepare__(name, bases, **new_def)
        # pdb.set_trace()
        # return super().__prepare__(name, bases, **new_def)

    def __new__(mcs, name, bases, clsdict, **kwargs):
        return type.__new__(mcs, name, bases, clsdict)

    def __init__(cls, name, bases, namespace, **kwargs):
        super().__init__(name, bases, namespace)


class RdfLinkedPropertyMeta(RdfPropertyMeta):
    """ Metaclass for generating rdfproperty classes """

    @classmethod
    def __prepare__(mcs, name, bases, **kwargs):
        # print('  RdfClassMeta.__prepare__(\n\t\t%s)' % (p_args(args, kwargs)))

        cls_name = kwargs.pop('cls_name')
        if cls_name == 'RdfClassBase':
            return {}
        linked_cls = kwargs.pop('linked_cls')
        prop_defs = {attr: getattr(bases[0], attr)
                     for attr in dir(bases[0])
                     if isinstance(attr, Uri.__wrapped__)}
        prop_name = bases[0]._prop_name

        new_def = filter_prop_defs(prop_defs,
                                   linked_cls.hierarchy,
                                   [cls_name])
        new_def['__doc__'] = bases[0].__doc__
        new_def['_cls_name'] = cls_name
        new_def['_linked_cls'] = linked_cls
        new_def['_prop_name'] = prop_name
        new_def['_init_processors'] = get_processors('kds_initProcessor',
                                                     new_def)
        new_def['_es_processors'] = get_processors('kds_esProcessor',
                                                   new_def)
        return new_def
        # x = super().__prepare__(name, bases, **new_def)
        # pdb.set_trace()
        # return super().__prepare__(name, bases, **new_def)

    # def __new__(mcs, name, bases, clsdict, **kwargs):
    #     return type.__new__(mcs, name, bases, clsdict)

    # def __init__(cls, name, bases, namespace, **kwargs):
    #     super().__init__(name, bases, namespace)

class RdfPropertyBase(list): #  metaclass=RdfPropertyMeta):
    """ Property Base Class """




    def __init__(self, bound_class, dataset=None):
        super().__init__(self)
        self.dataset = dataset
        self.bound_class = bound_class
        self.class_names = bound_class.class_names
        self.old_data = []
        try:
            self._run_processors(self._init_processors)
        except AttributeError:
            pass

    def __call__(self, bound_class, dataset=None):
        self.dataset = dataset
        self.bound_class = bound_class
        self.old_data = []

    def _run_processors(self, processor_list):
        """ cycles through a list of processors and runs them

        Args:
            processor_list(list): a list of processors
        """
        for processor in processor_list:
            processor(self)

    @classmethod
    def es_mapping(cls, base_class, **kwargs):
        """ Returns the es mapping for the property
        """

        es_map = {}
        ranges = cls.rdfs_range # pylint: disable=no-member
        rng_defs = get_prop_range_defs(cls.class_names, cls.kds_rangeDef)
        rng_def = get_prop_range_def(rng_defs)
        if rng_def.get("kds_esIndexClass"):
            ranges = rng_def['kds_esIndexClass'].copy()
        # pdb.set_trace()
        # if cls._prop_name == "bf_partOf":
        #     pdb.set_trace()
        idx_types = get_idx_types(rng_def, ranges)
        if 'es_Ignored' in idx_types:
            return {'type': 'text',
                    'index': es_idx_types['es_NotIndexed']}
        if 'es_Nested' in idx_types:
            if (kwargs.get('depth', 0) >= 1 and \
                    kwargs.get('class') == ranges[0]) or \
                    kwargs.get('depth', 0) > 2:
                return {"type" : "keyword"}
            nested_map = getattr(MODULE.rdfclass,
                                 ranges[0]).es_mapping(base_class,
                                                       'es_Nested',
                                                       **kwargs)
            es_map['properties'] = nested_map
            es_map['type'] = "nested"
        elif len(idx_types) > 1:
            fields = {}
            for idx in idx_types:
                fields.update(es_idx_types[idx])
            es_map['fields'] = fields
        elif len(idx_types) == 1:
            if cls._prop_name == 'rdf_type': # pylint: disable=no-member
                es_map['type'] = 'keyword'
            elif idx_types[0] == 'es_NotIndexed':
                es_map['index'] = False
            else:
                es_map['type'] = es_idx_types[idx_types[0]]
        try:
            if not es_map.get('type'):
                fld_type = BaseRdfDataType[ranges[0]].es_type
                es_map['type'] = fld_type
                if cls._prop_name == 'rdf_type':
                    es_map['type'] = 'keyword'
        except (KeyError, AttributeError):
            if cls._prop_name == 'rdf_type': # pylint: disable=no-member
                es_map['type'] = 'keyword'
            else:
                es_map['type'] = 'text'
        if es_map['type'] == "nested":
            del es_map['type']
        try:
            fld_format = BaseRdfDataType[ranges[0]].es_format
            es_map['format'] = fld_format
        except (KeyError, AttributeError):
            pass
        return es_map

    @classmethod
    def es_indexers(cls, base_class, **kwargs):
        """ Returns the es mapping for the property
        """
        indexer_list = []
        ranges = cls.rdfs_range # pylint: disable=no-member
        rng_defs = get_prop_range_defs(cls.class_names, cls.kds_rangeDef)
        rng_def = get_prop_range_def(rng_defs)
        if rng_def.get("kds_esIndexClass"):
            ranges = rng_def['kds_esIndexClass'].copy()
        idx_types = get_idx_types(rng_def, ranges)
        if 'es_Ignored' in idx_types:
            return []
        if 'es_Nested' in idx_types:
            if (kwargs.get('depth', 0) >= 1 and \
                    kwargs.get('class') == ranges[0]) or \
                    kwargs.get('depth', 0) > 2:
                return []
            indexer_list = getattr(MODULE.rdfclass,
                                   ranges[0]).es_indexers(base_class,
                                                          'es_Nested',
                                                          **kwargs)
        return indexer_list

    def es_json(self, **kwargs):
        """ Returns a JSON object of the property for insertion into es
        """
        rtn_list = []
        rng_defs = get_prop_range_defs(self.class_names, self.kds_rangeDef)
        # if self.__class__._prop_name == 'bf_partOf':
        #     pdb.set_trace()
        rng_def = get_prop_range_def(rng_defs)
        idx_types = rng_def.get('kds_esIndexType', []).copy()
        if 'es_Ignore' in idx_types:
            return rtn_list
        ranges = self.rdfs_range # pylint: disable=no-member
        # copy the current data into the es_values attribute then run
        # the es_processors to manipulate that data
        self.es_values = self.copy()
        # determine if using inverseOf object
        if rng_def.get('kds_esLookup'):
            self.es_values += self.dataset.json_qry("%s.$" % getattr(self,
                    rng_def['kds_esLookup'][0])[0].pyuri,
                    {'$':self.bound_class.subject})
            self.es_values = list(set(self.es_values))

        self._run_processors(self._es_processors)
        if not idx_types:
            nested = False
            for rng in ranges:
                if range_is_obj(rng, MODULE.rdfclass):
                    nested = True
                    break

            value_class = [value.__class__ for value in self.es_values
                           if isinstance(value, MODULE.rdfclass.RdfClassBase)]
            if value_class or nested:
                nested = True
            else:
                nested = False
            if nested:
                idx_types.append('es_Nested')
        rtn_obj = {}
        if 'es_Nested' in idx_types:
            if kwargs.get('depth', 0) > 6:
                return  [val.subject.sparql_uri for val in self]

            for value in self.es_values:
                try:
                    new_value = value.es_json('es_Nested', **kwargs)
                except AttributeError:
                    new_value = convert_value_to_es(value,
                                                    ranges,
                                                    self,
                                                    "missing_obj")
                rtn_list.append(new_value)
                if rng_def.get("kds_esField"):
                    es_value_fld = rng_def['kds_esValue'][0] \
                            if rng_def['kds_esValue'] else None
                    es_field = rng_def['kds_esField'][0]
                    for item in value.get(es_field):
                        if new_value.get(es_value_fld):
                            val = new_value.get(es_value_fld , [])
                            try:
                                rtn_obj[item.pyuri] += val
                            except KeyError:
                                rtn_obj[item.pyuri] = val
        else:
            for value in self.es_values:
                rtn_list.append(convert_value_to_es(value, ranges, self))
        if rtn_obj:
            return rtn_obj
        return rtn_list


def make_property(prop_defs, prop_name, cls_names=[], hierarchy=[]):
    """ Generates a property class from the defintion dictionary

    args:
        prop_defs: the dictionary defining the property
        prop_name: the base name of the property
        cls_name: the name of the rdf_class with which the property is
                  associated
    """
    register = False
    try:
        cls_names.remove('RdfClassBase')
    except ValueError:
        pass
    if cls_names:
        new_name = "%s_%s" % (prop_name.pyuri, "_".join(cls_names))
        prop_defs['kds_appliesToClass'] = cls_names
    elif not cls_names:
        cls_names = [Uri('kdr_AllClasses')]
        register = True
        new_name = prop_name
    else:
        new_name = prop_name

    new_prop = types.new_class(new_name,
                               (RdfPropertyBase, list,),
                               {'metaclass': RdfPropertyMeta,
                                'prop_defs': prop_defs,
                                'class_names': cls_names,
                                'prop_name': prop_name,
                                'hierarchy': hierarchy})
    if register:
        global properties
        global domain_props
        properties[new_name] = new_prop
        for domain in new_prop.rdfs_domain:
            try:
                # domain_props[domain].append(new_prop)
                domain_props[domain][prop_name] = prop_defs
            except KeyError:
                # domain_props[domain] = [new_prop]
                domain_props[domain] = {}
                domain_props[domain][prop_name] = prop_defs
            except TypeError:
                pass
    return new_prop


def link_property(prop, cls_object):
    """ Generates a property class linked to the rdfclass

    args:
        prop: unlinked property class
        cls_name: the name of the rdf_class with which the property is
                  associated
        cls_object: the rdf_class
    """
    register = False
    cls_name = cls_object.__name__
    if cls_name and cls_name != 'RdfBaseClass':
        new_name = "%s_%s" % (prop._prop_name, cls_name)
    else:
        new_name = prop._prop_name

    new_prop = types.new_class(new_name,
                               (prop,),
                               {'metaclass': RdfLinkedPropertyMeta,
                                'cls_name': cls_name,
                                'prop_name': prop._prop_name,
                                'linked_cls': cls_object})
    return new_prop

def get_properties(cls_def):
    """ cycles through the class definiton and returns all properties """
    # pdb.set_trace()
    prop_list = {prop: value for prop, value in cls_def.items() \
                 if 'rdf_Property' in value.get('rdf_type', "") or \
                 value.get('rdfs_domain')}

    return prop_list

# def get_idx_types(prop_name, prop_def):
#     if len(prop_def.rng_defs) > 1:
#         pass
#         #! write function to merge range defs
#     try:
#         rng_def = prop_def.rng_defs[0]
#     except IndexError:
#         rng_def = {}
#     idx_types = rng_def.get('kds_esIndexType', []).copy()
#     # pdb.set_trace()
#     try:
#         idx_types.remove('es_Standard')
#     except ValueError:
#         pass

#     if prop_name == "rdfs_label": # pylint: disable=no-member
#         idx_types += ['es_Raw', 'es_Lower']
#     if idx_types:
#         nested = False
#         for rng in ranges:
#             if hasattr(MODULE.rdfclass, rng) and \
#                     rng != 'rdfs_Literal' and \
#                     isinstance(getattr(MODULE.rdfclass, rng),
#                                MODULE.rdfclass.RdfClassMeta)\
#                     and cls._prop_name != 'rdf_type': # pylint: disable=no-member
#                 nested = True
#         if nested:
#             idx_types.append('es_Nested')

def filter_prop_defs(prop_defs, hierarchy, cls_names):
    """ Reads through the prop_defs and returns a dictionary filtered by the
        current class

    args:
        prop_defs: the defintions from the rdf vocabulary defintion
        cls_object: the class object to tie the property
        cls_names: the name of the classes
    """

    def _is_valid(test_list, valid_list):
        """ reads the list of classes in appliesToClass and returns whether
            the test_list matches

        args:
            test_list: the list of clasees to test against
            valid_list: list of possible matches
        """

        for test in test_list:
            if test in valid_list:
                return True
        return False

    new_dict = {}
    valid_classes = [Uri('kdr_AllClasses')] + cls_names + hierarchy
    for def_name, value in prop_defs.items():
        new_dict[def_name] = []
        empty_def = []
        try:
            for item in value:
                if item.get('kds_appliesToClass'):
                    if _is_valid(item['kds_appliesToClass'], valid_classes):
                        new_dict[def_name].append(item)
                else:
                    empty_def.append(item)
            if not new_dict[def_name]:
                new_dict[def_name] = empty_def
        except AttributeError:
            new_dict[def_name] = value
    return new_dict

def prepare_prop_defs(prop_defs, prop_name, cls_names):
    """
    Examines and adds any missing defs to the prop_defs dictionary for
    use with the RdfPropertyMeta.__prepare__ method

    Args:
    -----
        prop_defs: the defintions from the rdf vocabulary defintion
        prop_name: the property name
        cls_names: the name of the associated classes

    Returns:
    --------
        prop_defs
    """
    def get_def(prop_defs, def_fields, default_val=None):
        """ returns the cross corelated fields for delealing with mutiple
            vocabularies

        args:
            prop_defs: the propertry definition object
            def_fields: list of the mapped field names
            default_val: Default value if none of the fields are found
        """
        rtn_list = []
        for fld in def_fields:
            if prop_defs.get(fld):
                rtn_list += prop_defs.get(fld)
        if not rtn_list and default_val:
            rtn_list.append(default_val)
        elif rtn_list:
            try:
                rtn_list = list(set(rtn_list))
            except TypeError as e:
                # This deals with a domain that required a conjunction of two
                # rdf_Classes
                # pdb.set_trace()
                new_rtn = []
                for item in rtn_list:
                    if isinstance(item, MODULE.rdfclass.RdfClassBase):
                        new_rtn.append(\
                                "|".join(merge_rdf_list(item['owl_unionOf'])))
                    elif isinstance(item, list):
                        new_rtn.append("|".join(item))
                    else:
                        new_rtn.append(item)
                rtn_list = list(set(new_rtn))
                new_rtn = []
                for item in rtn_list:
                    if "|" in item:
                        new_rtn.append([Uri(domain) \
                                        for domain in item.split("|")])
                    else:
                        new_rtn.append(Uri(item))
                rtn_list = new_rtn

                # pdb.set_trace()
        return rtn_list

    required_def_defaults = {
        Uri('kds_rangeDef'): [{}],
        Uri('rdfs_range'): [Uri("xsd_string")],
        Uri('rdfs_domain'): cls_names,
        Uri('rdfs_label'): [NSM.nouri(prop_name)],
        Uri('kds_formDefault'): [{
            Uri('kds:appliesToClass'): Uri('kdr:AllClasses'),
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
    for prop in required_def_defaults:
        if prop not in prop_defs.keys():
            prop_defs[prop] = required_def_defaults[prop]
    prop_defs['rdfs_domain'] = get_def(prop_defs, DOMAIN_FIELDS, cls_names)
    prop_defs['rdfs_range'] = get_def(prop_defs, RANGE_FIELDS,
                                      Uri('xsd_string'))

    return prop_defs

def tie_prop_to_class(prop, cls_name):
    """ reads through the prop attributes and filters them for the associated
    class and returns a dictionary for meta_class __prepare__

    args:
        prop: class object to read
        cls_name: the name of the class to tie the porperty to
    """
    attr_list = [attr for attr in dir(prop) if type(attr, Uri)]
    prop_defs = kwargs.pop('prop_defs')
    prop_name = kwargs.pop('prop_name')
    cls_name = kwargs.pop('cls_name')
    if cls_name == 'RdfClassBase':
        return {}
    doc_string = make_doc_string(name,
                                 prop_defs,
                                 bases,
                                 None)
    new_def = prepare_prop_defs(prop_defs, prop_name, cls_name)
    new_def['__doc__'] = doc_string
    new_def['_cls_name'] = cls_name
    new_def['_prop_name'] = prop_name
    if prop_name == 'rdf_type':
        new_def['append'] = unique_append
    # if prop_name == 'rdf_type':
    #     pdb.set_trace()
    new_def['_init_processors'] = get_processors('kds_initProcessor',
                                                 prop_defs)
    new_def['_es_processors'] = get_processors('kds_esProcessor',
                                               prop_defs,
                                               'es_values')
    # pdb.set_trace()
    return new_def


def unique_append(self, value):
    """ function for only appending unique items to a list.
    #! consider the possibility of item using this to a set
    """
    if value not in self:
        try:
            super(self.__class__, self).append(Uri(value))
        except AttributeError as err:
            if isinstance(value, MODULE.rdfclass.RdfClassBase):
                super(self.__class__, self).append(value)
            else:
                raise err

def get_processors(processor_cat, prop_defs, data_attr=None):
    """ reads the prop defs and adds applicable processors for the property

    Args:
        processor_cat(str): The category of processors to retreive
        prop_defs: property defintions as defined by the rdf defintions
        data_attr: the attr to manipulate during processing.

    Returns:
        list: a list of processors
    """
    processor_defs = prop_defs.get(processor_cat,[])
    processor_list = []
    for processor in processor_defs:
        proc_class = PropertyProcessor[processor['rdf_type'][0]]
        processor_list.append(proc_class(processor.get('kds_params', [{}]),
                                         data_attr))
    return processor_list


def merge_rdf_list(rdf_list):
    """ takes an rdf list and merges it into a python list

    args:
        rdf_list: the RdfDataset object with the list values

    returns:
        list of values
    """
    # pdb.set_trace()
    if isinstance(rdf_list, list):
        rdf_list = rdf_list[0]
    rtn_list = []
    # for item in rdf_list:
    item = rdf_list
    if item.get('rdf_rest') and item.get('rdf_rest',[1])[0] != 'rdf_nil':
        rtn_list += merge_rdf_list(item['rdf_rest'][0])
    if item.get('rdf_first'):
        rtn_list += item['rdf_first']
    rtn_list.reverse()
    return rtn_list


