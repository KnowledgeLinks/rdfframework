from rdfframework.utilities import KeyRegistryMeta

class TriplestoreConnection(metaclass=KeyRegistryMeta):
    __required_idx_attrs__ = ['vendor']
    pass

