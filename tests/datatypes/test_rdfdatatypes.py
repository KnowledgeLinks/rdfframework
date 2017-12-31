__author__ = "Jeremy Nelson, Mike Stabile"

import json
import os
import rdflib
import sys
import unittest
import datetime
import pdb

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
        self.test_lang_options = [{'type': 'literal',
                                   'value': 'test lang string',
                                   'xml:lang': 'en'},
                                  {'type': 'literal',
                                   'value': 'test lang string',
                                   'lang': 'en'}]


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

    def test_lang_equality(self):
        """ Tests to see if the value paramaters work of lang creation and then
        tests for equality  between each option """
        values = [rdt.XsdString(value) for value in self.test_lang_options]
        self.assertTrue(len(set(values)) == 1)

class Test_XsdBool(unittest.TestCase):
    """docstring for Test_XsdBool"""
    def setUp(self):
        self.true_inputs = [True, "1", 1, "true", "True"]
        self.false_inputs = [False, "0", "false", "False"]
        self.error_inputs = [None, "adfa"]
        self.test_sparql_values = [(True,'"true"^^xsd:boolean'),
                                   (False, '"false"^^xsd:boolean')]

    def test_true(self):
        for value in self.true_inputs:
            self.assertTrue(rdt.XsdBoolean(value))

    def test_false(self):
        for value in self.false_inputs:
            self.assertFalse(rdt.XsdBoolean(value))

    def test_errors(self):
        for value in self.error_inputs:
            self.assertRaises(TypeError, lambda: rdt.XsdBoolean(value))

    def test_sparql_values(self):
        for tup in self.test_sparql_values:
            self.assertEqual(rdt.XsdBoolean(tup[0]).sparql, tup[1])


if __name__ == '__main__':
    unittest.main()
