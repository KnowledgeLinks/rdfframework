__author__ = "Jeremy Nelson, Mike Stabile"

import inspect
import unittest
import rdfframework.framework as framework

class TestRdfFrameworkSingleton(unittest.TestCase):

    def setUp(self):
        self.rdf_singleton = framework.RdfFrameworkSingleton("", tuple(), dict())

    def test_init(self):
        new_singleton = framework.RdfFrameworkSingleton("", tuple(), dict())
        self.assertIsInstance(self.rdf_singleton, 
                         framework.RdfFrameworkSingleton)

    def tearDown(self):
        pass
    
class TestRdfFramework(unittest.TestCase):

    def setUp(self):
        pass

    def test_init_raises_no_params(self):
        self.assertRaises(OSError, framework.RdfFramework)

    def tearDown(self):
        pass

if __name__ == "__main__":
    unitest.main()
