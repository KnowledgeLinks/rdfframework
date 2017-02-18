__author__ = "Jeremy Nelson, Mike Stabile"

import json
import os
import rdflib
import sys
import unittest

from unittest.mock import MagicMock, patch

PROJECT_DIR = os.path.abspath(os.curdir)
sys.path.append(PROJECT_DIR)

import rdfframework.rdfdatatypes as rdt
import testinitialization as ti


class Test_XsdString(unittest.TestCase):
    test_values = ["1",
                   1,
                   "how are you"
                   {"lang":"en", "value":"Hello"},
                   rdt.XsdString("xsd instance")]

    def test_str_instance(self):
        ''' Does the XsdClass test as an instance of the python str class '''
        self.assertTrue(isinstance(rdt.XsdString(self.test_values[0])))


