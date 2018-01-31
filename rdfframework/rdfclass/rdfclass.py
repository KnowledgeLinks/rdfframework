""" Module for generating RdfClasses. These classes are the base mode for
dealing with RDF data, conversion, validation and CRUD operations """
import pdb
from hashlib import sha1

# from rdfframework import rdfclass
from rdfframework.utilities import LABEL_FIELDS, VALUE_FIELDS, make_doc_string
from rdfframework.datatypes import BaseRdfDataType, Uri, BlankNode, RdfNsManager
from rdfframework.configuration import RdfConfigManager

__author__ = "Mike Stabile, Jeremy Nelson"

CFG = RdfConfigManager()
NSM = RdfNsManager()
MODULE = __import__(__name__)

# List of class names that will be excluded when examining the bases of a class
IGNORE_CLASSES = ['RdfClassBase', 'dict', 'list']

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
        if bases[:-1]:
            try:
                mcs._registry[bases[0].__name__].append(cls)
            except KeyError:
                mcs._registry[bases[0].__name__] = [cls]
        return cls

class RdfClassMeta(Registry):
    """ Metaclass for generating RdfClasses. This metaclass will take the
    rdf defined class defintions and convert them to a python class.
    """

    @property
    def doc(cls):
        """ Prints the docstring for the class."""
        print_doc(cls)

    @property
    def properties(cls):
        """ Lists the properties for the class

        Returns:
            list of properties
        """
        return list_properties(cls)

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
            new_def['properties'] = property(list_properties)
            # new_def['json_def'] = cls_defs
            new_def['hierarchy'] = list_hierarchy(name, bases)
            new_def['id'] = None
            new_def['class_names'] = [name]
            es_defs = es_get_class_defs(cls_defs, name)
            if hasattr(bases[0], 'es_defs'):
                es_defs.update(bases[0].es_defs)
            new_def['es_defs'] = es_defs
            new_def['uri'] = Uri(name).sparql_uri
            for prop, value in props.items():
                new_def[prop] = MODULE.rdfclass.make_property(value,
                                                       prop,
                                                       new_def['class_names'])
                # new_def[prop] = value
            if 'rdf_type' not in new_def.keys():
                new_def[Uri('rdf_type')] = MODULE.rdfclass.properties.get('rdf_type')
            new_def['cls_defs'] = cls_defs #cls_defs.pop(name)
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

    def __init__(self, subject=None, **kwargs):
        super().__init__(self)
        self.dataset = kwargs.get('dataset')
        self._initilize_props()
        self._set_subject(subject)

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
        except AttributeError:
            new_list = [self[pred]]
            new_list.append(obj)
            self[pred] = new_list
        except KeyError:
            try:
                new_prop = MODULE.rdfclass.properties[pred]
            except KeyError:
                new_prop = MODULE.rdfclass.make_property({},
                                                  pred, self.class_names)
            setattr(self,
                    pred,
                    new_prop)
            self[pred] = getattr(self, pred)(self, self.dataset)
            self[pred].append(obj)

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

        def _prop_filter(prop, value):
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
                      if _prop_filter(prop, value, kwargs)}
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
                if prop in nested_props:
                    # if prop == 'bf_shelfMark':
                    #     pdb.set_trace()
                    new_val = value.es_json(**kwargs)
                    if (remove_empty and new_val) or not remove_empty:
                        if len(new_val) == 1:
                            rtn_obj[prop] = new_val[0]
                        else:
                            rtn_obj[prop] = new_val

        if self.subject.type == 'uri':
            rtn_obj['uri'] = self.subject.sparql_uri
            try:
                path = ""
                for base in [self.__class__] + list(self.__class__.__bases__):

                    if hasattr(base, 'es_defs') and base.es_defs:
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
        except AttributeError:
            # an attribute error is cause when the class is an only
            # an instance of the BaseRdfClass. We will search the rdf_type
            # property and construct a label from rdf_type value
            if self.get('rdf_type'):
                rtn_obj['label'] = self['rdf_type'][-1].value[1]
            else:
                rtn_obj['label'] = "no_label"
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
                if value.startswith("_:"):
                    return BlankNode(value)
                else:
                    return Uri(value)
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
        try:
            for prop, prop_class in self.properties.items():
                # passing in the current dataset tie
                self[prop] = prop_class(self, self.dataset)
                setattr(self, prop, self[prop])
            bases = remove_parents(self.__class__.__bases__)
            for base in bases:
                if base.__name__ not in IGNORE_CLASSES:
                    base_name = Uri(base.__name__)
                    try:
                        self['rdf_type'].append(base_name)
                    except KeyError:
                        self[Uri('rdf_type')] = MODULE.rdfclass.make_property({},
                                'rdf_type',
                                self.__class__.__name__)(self, self.dataset)
                        self['rdf_type'].append(base_name)
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

def print_doc(self=None):
    """ simple function for print the classes docstring. Used for assigning
    a property value in a metaclass """
    print(self.__doc__)

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
    for key in rtn_dict.keys():
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
