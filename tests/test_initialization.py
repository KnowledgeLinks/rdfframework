"""    This module is used for setting an intial test configs and values for
the rdfframework """

import pdb
import unittest

import rdfframework.rdfclass

from config import config
from rdfframework.rdfdatatypes import rdfdatatypes as rdt, BaseRdfDataType, Uri
from rdfframework.framework import RdfFramework
from rdfframework.rdfdatasets import RdfDataset
from rdfframework.configuration import RdfConfigManager
from rdfframework.sparql import get_all_item_data

class TestSetupFrameworkInitialization(unittest.TestCase):

    def setUp(self):
        self.r = rdfframework.rdfclass

        self.rdf_framework = RdfFramework(reset=False, config=config)

        self.cfg = RdfConfigManager()

        self.item_uri = "<http://library.kean.edu/173849#Work>"
        self.conn = cfg.data_tstore
        self.data = get_all_item_data(item_uri, conn)
        self.x = RdfDataset(data, item_uri)

    def test_init_values(self):
        self.assertEquals(self.r, rdfframework.rdfclass)
        self.assertIsInstance(self.rdf_framework,
                              RdfFramework)
        self.assertEquals(self.item_iri,
                          "<http://library.kean.edu/173849#Work>")
