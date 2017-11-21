import unittest

import rdfframework.utilities.fileutilities as fileutilities

class TestSimpleFileUtilities_list_files(unittest.TestCase):

    def setUp(self):
        pass

    def test_empty_call(self):
       self.assertRaises(TypeError,
            fileutilities.list_files)

    def test_none_file_directory(self):
        self.assertRaises(AttributeError,
            fileutilities.list_files,
            None)

    def test_empty_str_file_directory(self):
        self.assertEqual(
            fileutilities.list_files(''),
            [])

    def tearDown(self):
        pass

if __name__ == "__main__":
    unittest.main()
