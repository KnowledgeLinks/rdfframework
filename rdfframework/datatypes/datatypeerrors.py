class NsPrefixExistsError(Exception):
    """	Exception raised for assigment of RdfNamespace 'prefix' if already
        defined with a different 'uri'.

    Attributes:
        new_ns: the new ns paramaters
        old_ns: the current ns patamaters
        message: explanation of the error
    """

    def __init__(self, new_ns, old_ns, message):
        self.new_ns = new_ns
        self.old_ns = old_ns
        self.message = message

class NsUriExistsError(Exception):
    """	Exception raised for assigment of RdfNamespace 'uri' if already defined
        with a different 'prefix'

    Attributes:
        new_ns: the new ns paramaters
        old_ns: the current ns patamaters
        message: explanation of the error
    """

    def __init__(self, new_ns, old_ns, message):
        self.new_ns = new_ns
        self.old_ns = old_ns
        self.message = message

class NsUriBadEndingError(Exception):
    """ Exception raised for a RdfNamespace 'uri' not ending in a '/' or '#'

    Attributes:
        message: explanation of the error
    """

    def __init__(self, message):
        self.message = message

    def __getattr__(self, attr):
        return None
