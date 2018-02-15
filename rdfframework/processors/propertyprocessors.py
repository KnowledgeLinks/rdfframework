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

class PropertyProcessor(object):
    def __use_processor__(self, prop):
        """
        Tests to see if the processor should be used for a particular instance
        of a calling property based on the tied rdfclass for the property
        """
        if not set(prop.classnames).difference(set(self.classnames)) < \
                prop.classnames:
            return False
        return True

class AddClassProcessor(object, metaclass=PropSingleton):
    """ adds the rdf:Class URI to the property's list of values

    Args:
        prop(RdfPropertyBase): The instance of the rdf property
    """
    def __init__(self, params=None, classnames=[]):
        self.params = params
        self.classnames = classnames

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
    def __init__(self, params=None, classnames=[]):
        self.params = params
        self.classnames = set(classnames)

    def __call__(self, prop):

        rtn_list = [item for item in prop.es_values]
        for prop_uri in prop.bound_class.hierarchy:
            rtn_list.append(prop_uri)
        prop.es_values = list(set(rtn_list))

prop_processor_mapping = {
    Uri('kdr:AddClassProcessor'): AddClassProcessor,
    Uri('kdr:AddClassHeirarchyProcessor'): AddClassHeirarchyProcessor
}
