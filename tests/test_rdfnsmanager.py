__author__ = "Jeremy Nelson, Mike Stabile"

import os
import sys
import unittest

PROJECT_DIR = os.path.abspath(os.curdir)
sys.path.append(PROJECT_DIR)
import rdfframework.utilities.uriconvertor as uriconvertor 

class TestConvertToNs(unittest.TestCase):

    def test_default_conversion(self):
        pass
        

if __name__ == '__main__':
    unittest.main()
