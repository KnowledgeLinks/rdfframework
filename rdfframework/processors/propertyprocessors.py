""" MODULE contains a Uri mapping to Rdf Property Processing class """

from rdfframework.datatypes import Uri
from rdfframework.utilities import KeyRegistryMeta

class PropSingleton(KeyRegistryMeta):
    """singleton class for processors that do not utilize any params  """

    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(PropSingleton,
                                        cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class PropertyProcessor(metaclass=KeyRegistryMeta):
    """
    Base class for all property processors. All subclasses are registered
    to this class. To add an addtional property processor outside of the
    rdfframework subclass this class and add a class attribute called

    'definition_uri' set as a rdfframework.datatypes.Uri instance of the
    property proccessor name

    Args:
    -----
        prop(RdfPropertyBase): The instance of the rdf property
        classnames: list of applied classnames
        data_attr: the name of the attribute to manipulate in the supplied
                property during the call

    """
    __required_idx_attrs__ = {"definition_uri"}
    __optional_idx_attrs__ = {"datatype", "py_type"}
    __special_idx_attrs__ = [{"datatype": ["sparql",
                                           "sparql_uri",
                                           "pyuri",
                                           "clean_uri",
                                           "rdflib"]}]
    __nested_idx_attrs__ = {"type"}

    def __init__(self, params=None, data_attr=None, classnames=[]):
        self.params = params
        self.classnames = set(classnames)
        self.data_attr = data_attr

    def __use_processor__(self, prop):
        """
        Tests to see if the processor should be used for a particular instance
        of a calling property based on the tied rdfclass for the property
        """
        if not set(prop.classnames).difference(set(self.classnames)) < \
                prop.classnames:
            return False
        return True

    def __data_source__(self, prop):
        """
        selects the appropraiate data source
        """
        if self.data_attr:
            return getattr(prop, self.data_attr)
        else:
            return prop

    def __set_data__(self, prop, data):
        """
        sets the processed data to the appropriated property attribute

        Args:
        -----
            prop: the property being manipulated
            data: the list of processed data
        """
        if self.data_attr:
            setattr(prop, self.data_attr, data)
        else:
            rm_idxs = []
            for i, val in enumerate(prop):
                if val not in data:
                    rm_idxs.append(i)
            for idx in sorted(rm_idxs, reverse=True):
                prop.pop(idx)
            for val in data:
                if val not in prop:
                    prop.append(val)

class AddClassProcessor(PropertyProcessor, metaclass=PropSingleton):
    """
    Adds the rdf:Class URI to the property's list of values
    """
    definition_uri = Uri('kdr:AddClassProcessor')

    def __call__(self, prop):
        prop += prop.bound_class.class_names

class AddClassHierarchyProcessor(PropertyProcessor, metaclass=PropSingleton):
    """
    Adds the rdf:Class hierarchy URIs to the property's list of values.
    This is useful for indexing in elasticsearch when dealing with rdf:type.
    This way when doing a term search for a particular rdf:type all of the
    subclasses for that type will be included as well.

    Example:
    --------

        For a property with 'schema_Person' as the associated class,
        ['schema:Thing', 'schema:Person'] will be added to the property list
        of values since 'schema:Person' is a subclass of 'schema:Thing'
    """

    definition_uri = Uri('kdr:AddClassHierarchyProcessor')

    def __call__(self, prop):
        data = self.__data_source__(prop)

        rtn_list = [item for item in data]
        for prop_uri in prop.bound_class.hierarchy:
            rtn_list.append(prop_uri)
        rtn_list = list(set(rtn_list))

        self.__set_data__(prop, rtn_list)

class ConvertObjectToStringProcessor(PropertyProcessor):
    """
    Converts the object values of the property to a string

    Args:
    -----
        params: {'kds_lookupProperty': the name of the rdf property in the
                                 object value to convert to a string}

    Returns:
    --------
        strings for each object value
    """
    definition_uri = Uri('kdr:ConvertObjectToStringProcessor')

    def __init__(self, params=[{}], data_attr=None, classnames=[]):
        super().__init__(params, data_attr, classnames)
        str_prop = params[0].get('kds_lookupProperty')
        if str_prop:
            self.str_prop = str_prop[0]
        else:
            self.str_prop = None



    def __call__(self, prop):
        data = self.__data_source__(prop)
        rtn_list = []
        if self.str_prop:
            for val in data:
                if val.get(self.str_prop):
                    rtn_list = [str(item) for item in val[self.str_prop]]
        else:
            rtn_list = [str(item) for item in data]

        self.__set_data__(prop, rtn_list)

