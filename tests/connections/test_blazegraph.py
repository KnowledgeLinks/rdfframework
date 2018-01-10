import unittest

import rdfframework.connections.blazegraph as blazegraph

class TestBlazegraphDefaultInit(unittest.TestCase):

    def setUp(self):
        pass

    def test_no_params(self):
        bz = blazegraph.Blazegraph()
        self.assertTrue(bz.url is not None)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
