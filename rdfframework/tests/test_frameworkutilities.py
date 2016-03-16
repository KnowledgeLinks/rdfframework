__author__ = "Jeremy Nelson, Mike Stabile"

import json
import os
import sys
import unittest



PROJECT_DIR = os.path.abspath(os.curdir)
sys.path.append(PROJECT_DIR)

from rdfframework.utilities.frameworkutilities import *

class Test_cbool(unittest.TestCase):

    def test_cbool(self):
        self.assertTrue(cbool(True))
        self.assertFalse(cbool(False))
        self.assertEqual(cbool(None), None)
        self.assertEqual(cbool(None, False), None)

    def test_cbool_str_true(self):
        self.assertTrue(cbool('true'))
        self.assertTrue(cbool('1'))
        self.assertTrue(cbool('t'))
        self.assertTrue(cbool('y'))
        self.assertTrue(cbool('yes'))

    def test_cbool_str_false(self):
        self.assertFalse(cbool('false'))
        self.assertFalse(cbool('0'))
        self.assertFalse(cbool('n'))
        self.assertFalse(cbool('no'))



class TestIri(unittest.TestCase):

    def test_iri(self):
        self.assertEqual(iri("https://schema.org/Person"), 
                         "<https://schema.org/Person>")
        self.assertEqual(iri("<obi:recipient>"),
                         "<obi:recipient>")

    def test_iri_errors(self):
        self.assertRaises(TypeError, iri, None)
        self.assertEqual(iri(""),
                         "<>")

class Test_is_not_null(unittest.TestCase):

    def test_is_not_null(self):
        self.assertFalse(is_not_null(None))
        self.assertFalse(is_not_null(""))

    def test_is_not_null_true(self):
        self.assertTrue(is_not_null("Test"))
        self.assertTrue(is_not_null(1234))      

class Test_make_list(unittest.TestCase):

    def test_make_list_dict(self):
        test_coordinates = { "x": 1, "y": 2}
        self.assertEqual(make_list(test_coordinates),
                         [test_coordinates,])
        
    def test_make_list_list(self):
        test_list = [1,2,3,4]
        self.assertEqual(make_list(test_list),
                         test_list)

    def test_make_list_str(self):
        test_str = "this is a string"
        self.assertEqual(make_list(test_str),
                         [test_str,])


class Test_nz(unittest.TestCase):

    def test_nz_none(self):
        self.assertEqual(
           nz(None, "a test"),
           "a test")

    def test_nz_empty_str_none_val(self):
        self.assertEqual(
            nz(None, ""),
            "")

    def test_nz_empty_str_val(self):
        self.assertEqual(
            nz("", "a test"),
            "")

    def test_nz_empty_str_val_strict(self):
        self.assertEqual(
            nz("", "a test", False),
            "a test")



