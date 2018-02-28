""" Module for generating RdfClasses. These classes are the base mode for
dealing with RDF data, conversion, validation and CRUD operations """
import pdb


# from rdfframework import rdfclass
from rdfframework.utilities import (LABEL_FIELDS,
                                    VALUE_FIELDS,
                                    make_doc_string,
                                    get_attr,
                                    RegistryDictionary,
                                    print_doc)
from rdfframework.datatypes import BaseRdfDataType, Uri, BlankNode, RdfNsManager
from rdfframework.configuration import RdfConfigManager
from rdfframework.rdfclass.esconversion import (get_es_value,
                                                get_es_label,
                                                get_prop_range_defs,
                                                get_prop_range_def,
                                                get_es_ids)

__author__ = "Mike Stabile, Jeremy Nelson"

CFG = RdfConfigManager()
NSM = RdfNsManager()
MODULE = __import__(__name__)

# List of class names that will be excluded when examining the bases of a class
IGNORE_CLASSES = ['RdfClassBase', 'dict', 'list']
__a__ = Uri("rdf:type")

def find(value):
        """
        returns a dictionary of rdfclasses based on the a lowercase search

        args:
            value: the value to search by
        """
        value = str(value).lower()
        rtn_dict = RegistryDictionary()
        for attr in dir(MODULE.rdfclass):
            if value in attr.lower():
                item = getattr(MODULE.rdfclass, attr)
                if issubclass(item, RdfClassBase):
                    rtn_dict[attr] = item
        return rtn_dict

class RegistryMeta(type):
    """ Registry meta class for use with the Registry class """
    def __getitem__(cls, key):
        try:
            return cls._registry[key]
        except KeyError:
            return []

class Registry(type, metaclass=RegistryMeta):
    """ Registery for for rdf class registration """
    _registry = {}

    def __new__(mcs, name, bases, clsdict):
        cls = super(Registry, mcs).__new__(mcs, name, bases, clsdict)
        # if the RdfClassBase is not in the bases then the class is merged
        # from multiple classes and should not be registred
        try:
            if RdfClassBase not in bases:
                return cls
        except NameError:
            pass
        if bases[:-1] and len(bases[0].class_names) == 1:
            # pdb.set_trace()
            try:
                mcs._registry[bases[0].__name__].append(cls)
            except KeyError:
                mcs._registry[bases[0].__name__] = [cls]
        return cls

def list_base_properties(bases):
    """ returns a dictionary of properties assigned to the class"""
    rtn_dict = {}
    for base in bases:
        if hasattr(base, 'properties'):
            rtn_dict.update(base.properties)
    return rtn_dict

class RdfClassMeta(Registry):
    """ Metaclass for generating RdfClasses. This metaclass will take the
    rdf defined class defintions and convert them to a python class.
    """

    @property
    def doc(cls):
        """ Prints the docstring for the class."""
        print_doc(cls)

    @property
    def subclasses(cls):
        return Registry[cls.__name__]

    @classmethod
    def __prepare__(mcs, name, bases, **kwargs):
        try:
            cls_defs = kwargs.pop('cls_defs')
            props = get_properties(name) #cls_defs)
            doc_string = make_doc_string(name,
                                         cls_defs,
                                         bases,
                                         props)
            new_def = {}
            # if name == 'bf_Topic': pdb.set_trace()
            new_def['__doc__'] = doc_string
            new_def['doc'] = property(print_doc)
            new_def['properties'] = list_base_properties(bases) #property(list_properties)
            # new_def['json_def'] = cls_defs
            new_def['hierarchy'] = list_hierarchy(name, bases)
            new_def['id'] = None
            new_def['class_names'] = [name]
            es_defs = es_get_class_defs(cls_defs, name)
            if hasattr(bases[0], 'es_defs'):
                es_defs.update(bases[0].es_defs)
            new_def['es_defs'] = es_defs
            new_def['query_kwargs'] = get_query_kwargs(es_defs)
            new_def['uri'] = Uri(name).sparql_uri
            for prop, value in props.items():
                new_def[prop] = MODULE.rdfclass.make_property(value,
                                                       prop,
                                                       new_def['class_names'])
                new_def['properties'][prop] = new_def[prop]
            if __a__ not in new_def.keys():
                new_def[__a__] = MODULE.rdfclass.properties.get(__a__)
                new_def['properties'][__a__] = new_def[__a__]
            new_def['cls_defs'] = cls_defs #cls_defs.pop(name)
            new_def['es_props'] = []
            for prop_name, prop in new_def['properties'].items():
                rng_def = get_prop_range_def(\
                            get_prop_range_defs(new_def['class_names'],
                                                prop.kds_rangeDef))
                if rng_def.get('kds_esLookup'):
                    new_def['es_props'].append(prop_name)
            return new_def
        except KeyError:
            return {}
            # return {'_cls_name': name}

    def __new__(mcs, name, bases, clsdict, **kwargs):
        return super().__new__(mcs, name, bases, clsdict)

    def __init__(cls, name, bases, namespace, **kwargs):
        super().__init__(name, bases, namespace)

class RdfClassBase(dict, metaclass=RdfClassMeta):
    """ This is the base class for the generation of all RDF Class type

    Args:
        sub: the instance URI for the rdf class. This is the subject URI

    Kwargs:
        dataset(RdfDataset): The linked RdfDataset that this instance of a class
                             is part.
    """
    class_names = []
    uri_format = 'sparql_uri'

    def __init__(self, subject=None, dataset=None, **kwargs):
        super().__init__(self)
        self.dataset = dataset
        self._set_subject(subject)
        if self.__class__ != RdfClassBase:
            self._initilize_props()


    def __hash__(self):
        return hash(self.subject)

    def __eq__(self, other):
        if self.subject == other:
            return True
        return False

    def add_property(self, pred, obj):
        """ adds a property and its value to the class instance

        args:
            pred: the predicate/property to add
            obj: the value/object to add
            obj_method: *** No longer used.
        """
        pred = Uri(pred)
        try:
            self[pred].append(obj)
        # except AttributeError:
        #     new_list = [self[pred]]
        #     new_list.append(obj)
        #     self[pred] = new_list
        except KeyError:
            try:
                new_prop = self.properties[pred]
            except AttributeError:
                self.properties = {}
                self.add_property(pred, obj)
                return
            except KeyError:
                try:
                    new_prop = MODULE.rdfclass.properties[pred]
                except KeyError:
                    new_prop = MODULE.rdfclass.make_property({},
                                                      pred, self.class_names)
                try:
                    self.properties[pred] = new_prop
                except AttributeError:
                    self.properties = {pred: new_prop}
            init_prop = new_prop(self, get_attr(self, "dataset"))
            setattr(self,
                    pred,
                    init_prop)
            self[pred] = init_prop
            self[pred].append(obj)
        if self.dataset:
            self.dataset.add_rmap_item(self, pred, obj)

    @property
    def subclasses(self):
        """ returns a list of sublcasses to the current class """
        return Registry[self.__class__.__name__]

    @property
    def to_json(self):
        """ converts the class to a json compatable python dictionary """
        return self.conv_json(self.uri_format)

    def conv_json(self, uri_format="sparql_uri", add_ids=False):
        """ converts the class to a json compatable python dictionary

        Args:
            uri_format('sparql_uri','pyuri'): The format that uri values will
                    be returned

        Returns:
            dict: a json compatabile python dictionary
        """
        def convert_item(ivalue):
            """ converts an idividual value to a json value

            Args:
                ivalue: value of the item to convert

            Returns:
                JSON serializable value
            """
            nvalue = ivalue
            if isinstance(ivalue, BaseRdfDataType):
                if ivalue.type == 'uri':
                    if ivalue.startswith("pyuri") and uri_format == "pyuri":
                        nvalue = getattr(ivalue, "sparql")
                    else:
                        nvalue = getattr(ivalue, uri_format)
                else:
                    nvalue = ivalue.to_json
            elif isinstance(ivalue, RdfClassBase):
                if ivalue.subject.type == "uri":
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

        def _prop_filter(prop, value, **kwargs):
            """ filters out props that should not be used for es_mappings:
            These include props that of the owl:inverseOf the parent_props.
            Use of these props will cause a recursion depth error

            Args:
                prop: the name of the prop
                value: the prop value(an instance of the prop's class)

            Returns:
                bool: whether the prop should be used
            """

            try:
                use_prop = len(set(value.owl_inverseOf) - parent_props) > 0
            except AttributeError:
                use_prop = True
            if not use_prop:
                print(prop)
            if prop in nested_props and use_prop:
                return True
            return False

        es_map = {}
        # pdb.set_trace()
        if kwargs.get("depth"): # and kwargs.get('class') == cls.__name__:
            kwargs['depth'] += 1
            initial = False
        else:
            initial = True
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

        elif role == 'es_Nested':
            # print(locals())
            # pdb.set_trace()
            if cls == base_class:
                nested_props = LABEL_FIELDS
            else:
                nested_props = cls.es_defs.get('kds_esNestedProps',
                                               list(cls.properties.keys()))
            es_map = {prop: value.es_mapping(base_class, **kwargs) \
                      for prop, value in cls.properties.items() \
                      if _prop_filter(prop, value, **kwargs)}
        ref_map = {
            "type" : "keyword"
        }
        ignore_map = {
            "index": False,
            "type": "text"
        }
        if cls == base_class:
            es_map['label'] = ref_map
            es_map['value'] = ref_map

        if cls.cls_defs.get('kds_storageType') != "blanknode" \
                and cls == base_class:
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
            remove_empty: True removes empty items from es object
        """
        # if self.__class__.__name__ == 'rdf_type':
        #     pdb.set_trace()
        rtn_obj = {}
        # pdb.set_trace()
        if kwargs.get("depth"):
            kwargs['depth'] += 1
        else:
            kwargs['depth'] = 1
        if role == 'rdf_Class':
            for prop, value in self.items():
                new_val = value.es_json()
                if (remove_empty and new_val) or not remove_empty:
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
                # if prop == 'rdfs_label' and 'bf_Organization' in self.class_names:
                #     pdb.set_trace()
                if prop in nested_props:
                    new_val = value.es_json(**kwargs)
                    if (remove_empty and new_val) or not remove_empty:
                        if len(new_val) == 1:
                            rtn_obj[prop] = new_val[0] \
                                    if not isinstance(new_val, dict) \
                                    else new_val
                        else:
                            rtn_obj[prop] = new_val
        # if 'bf_Work' in self.hierarchy:
        #     pdb.set_trace()
        rtn_obj = get_es_ids(rtn_obj, self)
        rtn_obj = get_es_label(rtn_obj, self)
        rtn_obj = get_es_value(rtn_obj, self)
        return rtn_obj

    def _set_subject(self, subject):
        """ sets the subject value for the class instance

        Args:
            subject(dict, Uri, str): the subject for the class instance
        """
        # if not subject:
        #     self.subject =
        def test_uri(value):
            """ test to see if the value is a uri or bnode

            Returns: Uri or Bnode """
            if not isinstance(value, (Uri.__wrapped__, BlankNode)):
                try:
                    if value.startswith("_:"):
                        return BlankNode(value)
                    else:
                        return Uri(value)
                except:
                    return BlankNode()
            else:
                return value

        if isinstance(subject, dict):
            self.subject = test_uri(subject['s'])
            if isinstance(subject['o'], list):
                for item in subject['o']:
                    self.add_property(subject['p'],
                                      item)
            else:
                self.add_property(subject['p'],
                                  subject['o'])
        else:
            self.subject = test_uri(subject)

    def _initilize_props(self):
        """ Adds an intialized property to the class dictionary """
        # if self.subject == "pyuri_aHR0cDovL3R1dHQuZWR1Lw==_":
        #     pdb.set_trace()
        try:
            # pdb.set_trace()
            for prop in self.es_props:
                self[prop] = self.properties[prop](self, self.dataset)
                setattr(self, prop, self[prop])
            # for prop, prop_class in self.properties.items():
            #     # passing in the current dataset tie
            #     self[prop] = prop_class(self, self.dataset)
            #     setattr(self, prop, self[prop])
            # bases = remove_parents((self.__class__,) +
            #                         self.__class__.__bases__)
            # for base in bases:
            #     if base.__name__ not in IGNORE_CLASSES:
            #         base_name = Uri(base.__name__)
            #         try:
            #             self['rdf_type'].append(base_name)
            #         except KeyError:
            #             self[Uri('rdf_type')] = MODULE.rdfclass.make_property({},
            #                     'rdf_type',
            #                     self.__class__.__name__)(self, self.dataset)
            #             self['rdf_type'].append(base_name)
        except (AttributeError, TypeError):
            pass

    @property
    def sparql(self):
        return self.subject.sparql

    @property
    def rdflib(self):
        return self.subject.rdflib

    @property
    def sparql_uri(self):
        return self.subject.sparql_uri



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

def es_get_class_defs(cls_def, cls_name):
    """ reads through the class defs and gets the related es class
        defintions

    Args:
        class_defs: RdfDataset of class definitions
    """
    # cls_def = cls_defs[cls_name]
    rtn_dict = {key: value for key, value in cls_def.items() \
                if key.startswith("kds_es")}
    for key in rtn_dict:
        del cls_def[key]
    return rtn_dict


def list_properties(cls):
    """ returns a dictionary of properties assigned to the class"""
    rtn_dict = {}
    for attr in dir(cls):
        if attr not in ["properties", "__doc__", "doc"]:
            attr_val = getattr(cls, attr)

            if isinstance(attr_val, MODULE.rdfclass.RdfPropertyMeta):
                rtn_dict[attr] = attr_val
    return rtn_dict

def get_properties(cls_name):
    """ cycles through the class definiton and returns all properties """
    # pdb.set_trace()

    # prop_list = {prop: value for prop, value in cls_def.items() \
    #              if 'rdf_Property' in value.get('rdf_type', "") or \
    #              value.get('rdfs_domain') or value.get('schema_domainIncludes')}

    # prop_list = {prop._prop_name: prop
    #              for prop in rdfclass.domain_props.get(cls_name, {})}
    prop_list = MODULE.rdfclass.domain_props.get(cls_name, {})
    return prop_list

def remove_parents(bases):
    """ removes the parent classes if one base is subclass of
        another"""
    if len(bases) < 2:
        return bases
    remove_i = []
    bases = list(bases)
    for i, base in enumerate(bases):
        for j, other in enumerate(bases):
            # print(i, j, base, other, remove_i)
            if j != i and (issubclass(other, base) or base == other):
                remove_i.append(i)
    remove_i = set(remove_i)
    remove_i = [i for i in remove_i]
    remove_i.sort(reverse=True)
    for index in remove_i:
        try:
            del bases[index]
        except IndexError:
            print("Unable to delete base: ", bases)
    return bases

def get_query_kwargs(es_defs):
    """
    Reads the es_defs and returns a dict of special kwargs to use when
    query for data of an instance of a class

    reference: rdfframework.sparl.queries.sparqlAllItemDataTemplate.rq
    """
    rtn_dict = {}
    if es_defs:
        if es_defs.get("kds_esSpecialUnion"):
            rtn_dict['special_union'] = \
                    es_defs["kds_esSpecialUnion"][0]
        if es_defs.get("kds_esQueryFilter"):
            rtn_dict['filters'] = \
                    es_defs["kds_esQueryFilter"][0]
    return rtn_dict
