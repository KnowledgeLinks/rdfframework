__author__ = "Jeremy Nelson"

import unittest
try:
    from .test_correctionqueries import *
    from .test_querygenerator import *
    from .queries import *
except ModuleNotFoundError:
    from test_correctionqueries import *
    from test_querygenerator import *
    from queries import *

if __name__ == "__main__":
    unittest.main()
