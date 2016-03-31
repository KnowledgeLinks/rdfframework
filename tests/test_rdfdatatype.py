__author__ = "Jeremy Nelson, Mike Stabile"

import unittest

from rdfframework.rdfdatatype import RdfDataType
from unittest.mock import MagicMock, patch


class TestRdfDatatype(unittest.TestCase):

    @patch("rdfframework.rdfdatatype.rdfw")
    def setUp(self, mock_rdfw):
        print("Iin setup {}".format(mock_rdfw))
        #self.langstring_instance = RdfDataType("langstring")
        #self.literal_instance = RdfDataType("literal")
        #self.obj_instance = RdfDataType("object")
        #self.str_instance = RdfDataType("http://www.w3.org/2001/XMLSchema#string")

    #@patch("rdfframework.utilities.frameworkutilities.FRAMEWORK_CONFIG")
    def test_init(self):#, mock_get_framework):
        print("in init")
        #instance = RdfDataType("https://schema.org/Person")
        #self.assertEqual(instance.name, "string")
        #self.assertEqual(
        #    instance.iri, 
        #    "<http://www.w3.org/2001/XMLSchema#string>")
        #self.assertEqual(instance.prefix, "xsd:string")

    @patch("rdfframework.rdfdatatype.rdfw")
    def test_init_errors(self, mock_get_framework):
        self.assertRaises(AttributeError, RdfDataType)
####
##    def test_literal_datatype(self):
##        self.assertEqual(self.literal_instance.name, "literal")
##        self.assertEqual(self.literal_instance.prefix, "rdf:literal")
##        self.assertEqual(
##            self.literal_instance.iri,
##            "<http://www.w3.org/1999/02/22-rdf-syntax-ns#literal>")
##
##
##    def test_langstring_datatype(self):
##        self.assertEqual(self.langstring_instance.prefix, "rdf:langstring")
##        self.assertEqual(
##            self.langstring_instance.iri,
##            "<http://www.w3.org/1999/02/22-rdf-syntax-ns#langstring>")
##
##
##    def test_object_datatype(self):
##        self.assertEqual(self.obj_instance.prefix, "objInject")
##        self.assertEqual(self.obj_instance.uri, "objInject")
##        self.assertEqual(
##            self.obj_instance.iri, 
##            "<http://www.w3.org/2001/XMLSchema#object>")
##
##        
##    def test_str_datatype(self):
##        self.assertEqual(self.str_instance.prefix, "xsd:string")
##        self.assertEqual(
##            self.str_instance.iri,
##            "<http://www.w3.org/2001/XMLSchema#string>")
##
##    def test_sparql_object(self):
##        self.assertEqual(
##            self.obj_instance.sparql("http://knowledgelinks.io/example/1"),
##            "<http://knowledgelinks.io/example/1>")
##        self.assertEqual(
##            self.obj_instance.sparql("Test String"),
##            "<Test String>")
##
##    def test_sparql_langstring(self):
##        self.assertEqual(
##            self.langstring_instance.sparql("eng"),
##            '"eng"^^rdf:langstring')
##
##
##    def test_sparql_literal(self):
##        self.assertEqual(
##            self.str_instance.sparql("Test String"),
##            '"Test String"^^xsd:string')
##
##    def test_sparql_boolean(self):
##        boolean_instance = RdfDataType("boolean")
##        self.assertEqual(
##            boolean_instance.sparql(True),
##            '"true"^^xsd:boolean')
##
##            
##    def test_sparql(self):
##        badge_class_instance = RdfDataType(str(DC.name))
##        self.assertEqual(
##            badge_class_instance.sparql("Test"),
##            '"Test"^^xsd:string')
