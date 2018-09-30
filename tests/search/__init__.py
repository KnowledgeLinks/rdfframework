__author__ = "Jeremy Nelson"
import unittest
try:
    from .test_esmappings import *
    from .test_esutilities import *
    from .test_elasticsearchbase import *
    from .test_esloaders import *
except ModuleNotFoundError:
    from test_esmappings import *
    from test_esutilities import *
    from test_elasticsearchbase import *
    from test_esloaders import *

if __name__ == "__main__":
    unittest.main()
