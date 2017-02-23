__author__ = "Jeremy Nelson, Mike Stabile"

import os
import unittest

import rdflib
from rdfframework.rdfdatatypes.rdfdatatypes import BaseRdfDataType, nsm
from unittest.mock import MagicMock, patch

DC = rdflib.Namespace("http://dublincore.org/documents/dcmi-namespace/")

class TestBaseRdfDatatype(unittest.TestCase):

    
    #@patch("rdfframework.rdfdatatype.rdfw")
    @patch("rdfframework.framework.RdfFramework")
    def setUp(self, mock_rdfw):
        mock_rdfw.root = os.path.abspath(__name__)
        self.base_type = BaseRdfDataType("This is a literal value")

    @patch("rdfframework.framework.RdfFramework")
    def test_init(self, mock_rdfw):
        #mock_rdfw.root = os.path.abspath(__name__)
        self.assertEqual(self.base_type.value,
                         "This is a literal value")
        
    def test_format_default(self):
        self.assertEqual(self.base_type._format(),
                         '"This is a literal value"^^xsd:string')

    def test_format_none(self):
        self.assertEqual(self.base_type._format(method=None),
                         '"This is a literal value"')

    def test_format_pyuri(self):
        self.assertEqual(self.base_type._format(method='pyuri'),
                         "<This is a literal value>")

