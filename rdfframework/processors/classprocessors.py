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

class ClassProcessor(metaclass=KeyRegistryMeta):
    """
    Base class for all class processors. All subclasses are registered
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

    def __use_processor__(self, rdf_class):
        """
        Tests to see if the processor should be used for a particular instance
        of a calling property based on the tied rdfclass for the property
        """
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
        pass


