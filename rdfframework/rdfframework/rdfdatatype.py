__author__ = "Mike Stabile, Jeremy Nelson"
from flask import json
from rdflib import RDF, RDFS, OWL, XSD

from rdfframework.utilities import iri, uri, make_list, xsd_to_python
from .getframework import get_framework as rdfw

class RdfDataType(object):
    "This class will generate a rdf data type"

    def __init__(self, rdf_data_type=None, **kwargs):
        if rdf_data_type is None:
            _class_uri = kwargs.get("class_uri")
            _prop_uri = kwargs.get("prop_uri")
            if _prop_uri:
                rdf_data_type = self._find_type(_class_uri, _prop_uri)
        self.lookup = uri(rdf_data_type)
        #! What happens if none of these replacements?
        val = self.lookup.replace(str(XSD), "").\
                replace("xsd:", "").\
                replace("rdf:", "").\
                replace(str(RDF), "")
        if "http" in val:
            val = "string"
        self.prefix = "xsd:{}".format(val)
        self.py_prefix = "xsd_%s" % val
        self.iri = iri("{}{}".format(str(XSD), val))
        self.name = val
        if val.lower() == "literal" or val.lower() == "langstring":
            self.prefix = "rdf:{}".format(val)
            self.iri = iri(str(RDF) + val)
        elif val.lower() == "object":
            self.prefix = "objInject"
            #! Why is uri a new property if an object?
            self.uri = "objInject"

    def sparql(self, data_value):
        "formats a value for a sparql triple"
        if self.name == "object":
            return iri(data_value)
        elif self.name == "literal":
            return '"{}"'.format(json.dumps(data_value))
        elif self.name == "boolean":
            return '"{}"^^{}'.format(str(data_value).lower(),
                                     self.prefix)
        else:
            formated_data = xsd_to_python(data_value, 
                                          self.py_prefix, 
                                          "literal",
                                          "string")
            return '{}^^{}'.format(json.dumps(data_value), self.prefix)

    def _find_type(self, class_uri, prop_uri):
        '''find the data type based on class_uri and prop_uri'''
        _rdf_class = getattr(rdfw(), class_uri)
        _range = make_list(_rdf_class.kds_properties.get(prop_uri).get(\
                "rdfs_range"))[0]
        _range.get("storageType")
        if _range.get("storageType") == "literal":
            _range = _range.get("rangeClass")
        else:
            _range = _range.get("storageType")
        return _range
