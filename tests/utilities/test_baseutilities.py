__author__ = "Jeremy Nelson, Mike Stabile"

import unittest
from rdfframework.utilities import baseutilities

class TestGetObjectFromString(unittest.TestCase):

    def setUp(self):
        pass

    def test_get_obj_frm_str_basic(self):
        self.assertEqual(baseutilities.get_obj_frm_str('str'),
                         str)
        self.assertEqual(baseutilities.get_obj_frm_str('dict'),
                         dict)

    def test_get_obj_frm_str_connection(self):
        from rdfframework.connections import ConnManager
        self.assertEqual(
            baseutilities.get_obj_frm_str(
                "rdfframework.connections.ConnManager"),
            ConnManager)


    def test_get_obj_frm_str_manager(self):
        from rdfframework.datatypes import RdfNsManager
        self.assertEqual(
            baseutilities.get_obj_frm_str("rdfframework.datatypes.RdfNsManager"),
            RdfNsManager)



    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
