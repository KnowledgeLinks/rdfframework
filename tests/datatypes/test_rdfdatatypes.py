__author__ = "Jeremy Nelson, Mike Stabile"

import json
import os
import rdflib
import sys
import unittest
import datetime

from unittest.mock import MagicMock, patch

import rdfframework.datatypes as rdt


class Test_XsdString(unittest.TestCase):

    def setUp(self):
        self.test_str_values = ["1",
                                "how are you",
                                rdt.XsdString("xsd instance")]
        self.test_non_str_values = [1,
                                    {"lang":"en", "value":"Hello"},
                                    datetime.datetime.now()]
        self.test_sparql_values = [({"lang":"en", "value":"lang_dict"},
                                    '"lang_dict"@en'),
                                   ({"value": "dict"}, '"dict"^^xsd:string'),
                                   ("str_input", '"str_input"^^xsd:string'),
                                   (1, '"1"^^xsd:string')]


    def test_str_instance(self):
        ''' Does the XsdClass test as an instance of the python str class '''
        self.assertTrue(isinstance(self.test_str_values[-1],
                                   rdt.XsdString))

    def test_str_equality(self):
        for value in self.test_str_values:
            self.assertEqual(value, rdt.XsdString(value))
            self.assertEqual(rdt.XsdString(value), value)

    def test_sparql_values(self):
        for tup in self.test_sparql_values:
            self.assertEqual(rdt.XsdString(tup[0]).sparql, tup[1])

if __name__ == '__main__':
    unittest.main()
