import unittest

import rdfframework.connections.blazegraph as blazegraph

class TestBlazegraphDefaultInit(unittest.TestCase):

    def setUp(self):
        pass

    def test_no_params(self):
        self.assertTrue(blazegraph.Blazegraph().url is not None)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
