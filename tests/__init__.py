import unittest


if __name__ == '__main__':
    from test_rdfwconfig import *
    from test_framework import *
    from connections.test_blazegraph import *
    from utilities.test_fileutilities import *
    from datatypes.test_rdfdatatypes import *
    from datatypes.test_namespaces import *
    unittest.main()
