import unittest
import logging
import rdfframework.connections.blazegraph as blazegraph

class TestBlazegraphDefaultInit(unittest.TestCase):

    def setUp(self):
        pass

    def test_no_params(self):
        blazegraph.log.setLevel(logging.CRITICAL)
        self.assertTrue(blazegraph.Blazegraph().ext_url is not None)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
