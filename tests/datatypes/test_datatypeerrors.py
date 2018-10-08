__author__ = "Jeremy Nelson, Mike Stabile"

import unittest

from rdfframework.datatypes.datatypeerrors import NsPrefixExistsError
from rdfframework.datatypes.namespaces import RdfNamespaceMeta

class TestNsPrefixExistsError(unittest.TestCase):

    def setUp(self):
        self.rdf_namespace_meta = RdfNamespaceMeta(
            "schema",
            (),
            {"schema": "http://schema.org/"})


    def test_namespace_uri_mismatch(self):
        self.assertRaises(NsPrefixExistsError, 
            self.rdf_namespace_meta._is_new_ns__, 
            self.rdf_namespace_meta, 
            {"schema": "http://wrong.info"})    

    def tearDown(self):
        pass

if __name__ == "__main__":
    unittest.main()
