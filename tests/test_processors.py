__author__ = "Jeremy Nelson, Mike Stabile"

import unittest
from unittest.mock import MagicMock, patch

from rdfframework.processors import csv_to_multi_prop_processor

class Test_csv_to_multi_prop_processor(unittest.TestCase):

    def setUp(self):
       self.tags = {}
      
    def test_load_mode(self):
        self.tags["prop"] = {"new": "orange"}
        self.tags["dataValue"] = ["red", "green", "blue", "yellow"]
        result = csv_to_multi_prop_processor(None, self.tags, "load")
        self.assertEqual(
            result,
            "red, green, blue, yellow")
##
##
##    def test_save_mode(self):
##        self.tags["prop"] = {"new": "red, green, blue, yellow"}
##        self.tags["processedData"] = {}
##        #result = csv_to_multi_prop_processor(self.tags)
##        #self.assertTrue(result['prop']['calcValue'])
##        #self.assertListEqual(
##        #    sorted(result['processedData'][self.tags.get('propUri')]),
##        #    sorted(["red", "green", "blue", "yellow"]))
##        #result2 = csv_to_multi_prop_processor(self.tags, "save")
##        #self.assertEqual(result, result2)
##
##
##    def test_unknown_mode(self):
##        pass
##        #! Should an unknown mode raise an error instead of returning the
##        #! object?
##        #self.assertEqual(
##        #    self.tags,
##        #    csv_to_multi_prop_processor(self.tags, "unknown"))

