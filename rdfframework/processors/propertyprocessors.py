""" MODULE contains a Uri mapping to Rdf Property Processing class """

from rdfframework.datatypes import Uri
# from rdfframework.rdfclass import RdfClassBase

class PropSingleton(type):
    """singleton class for processors that do not utilize any params  """

    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(PropSingleton,
                                        cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class AddClassProcessor(object, metaclass=PropSingleton):
    """ adds the rdf:Class URI to the property's list of values

    Args:
        prop(RdfPropertyBase): The instance of the rdf property
    """
    def __init__(self, params=None):
        self.params = params

    def __call__(self, prop):
        prop += prop.bound_class.class_names

class AddClassHeirarchyProcessor(object, metaclass=PropSingleton):
    """ adds the rdf:Class heirarchy URIs to the property's list of values.
    This is useful for indexing in elasticsearch when dealing with rdf:type.
    This way when doing a term search for a particular rdf:type all of the
    subclasses for that type will be included as well.

    Args:
        prop(RdfPropertyBase): The instance of the rdf property
        params: None
    Example:
        For a property with 'schema_Person' as the associated class,
        ['schema:Thing', 'schema:Person'] will be added to the property list
        of values since 'schema:Person' is a subclass of 'schema:Thing'
    """
    def __init__(self, params=None):
        self.params = params

    def __call__(self, prop):
        for prop_uri in prop.bound_class.heirarchy:
            prop.append(prop_uri)

prop_processor_mapping = {
    Uri('kdr:AddClassProcessor'): AddClassProcessor,
    Uri('kdr:AddClassHeirarchyProcessor'): AddClassHeirarchyProcessor
}
