import base64
from rdflib import URIRef
def http_formatter(namespace, value):
    """ Formats a namespace and ending value into a full RDF URI format with NO
    '<' and '>' encapsulation

    args:
        namespace: RdfNamespace or tuple in the format of (prefix, uri,)
        value: end value to attach to the namespace
    """
    return "%s%s" % (namespace[1], value)

def uri_formatter(namespace, value):
    """ Formats a namespace and ending value into a full RDF URI format with
    '<' and '>' encapsulation

    args:
        namespace: RdfNamespace or tuple in the format of (prefix, uri,)
        value: end value to attach to the namespace
    """
    return "<%s%s>" % (namespace[1], value)

def ttl_formatter(namespace, value):
    """ Formats an RdfNamespace in the RDF turtle format if able otherwise
    returns the full RDF URI format

    args:
        namespace: RdfNamespace of tuple in the format of (prefix, uri)
        value: end value to attach to the RdfNamespace
    """
    # if the namespce prefix exists format in ttl format
    if namespace[0]:
        return "%s:%s" % (namespace[0], value)
    else:
    # else return in full Uri format
        return uri_formatter(namespace, value)

def pyuri_formatter(namespace, value):
    """ Formats a namespace and ending value into a python friendly format

    args:
        namespace: RdfNamespace or tuple in the format of (prefix, uri,)
        value: end value to attach to the namespace
    """
    if namespace[0]:
        return "%s_%s" %(namespace[0], value)
    else:
        return "pyuri_%s_%s" % (base64.b64encode(bytes(namespace[1],
                                                       "utf-8")).decode(),
                                value)

def rdflib_formatter(namespace, value):
    """ formats the URI as an 'rdflib' URIRef

    args:
        namespace: RdfNamespace or tuple in the format of (prefix, uri,)
        value: end value to attach to the namespace
    """
    return URIRef(http_formatter(namespace, value))

def xmletree_formatter(namespace, value):
    """ formats the URI as an 'rdflib' URIRef

    args:
        namespace: RdfNamespace or tuple in the format of (prefix, uri,)
        value: end value to attach to the namespace
    """
    return "{%s}%s" % (namespace[1], value)
