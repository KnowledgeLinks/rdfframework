__author__ = "Jeremy Nelson"

import unittest
try:
    from .test_baseutilities import *
    from .test_mapreduce import *
    from .test_codetimer import *
    from .test_metaclasses import *
    from .test_colors import *
    from .test_rdfvocabcorrelations import *
    from .test_debug import *
    from .test_statistics import *
    from .test_fileutilities import *
    from .test_valuecalculator import *
    from .test_formattingfunctions import *
except ModuleNotFoundError:
    from test_baseutilities import *
    from test_mapreduce import *
    from test_codetimer import *
    from test_metaclasses import *
    from test_colors import *
    from test_rdfvocabcorrelations import *
    from test_debug import *
    from test_statistics import *
    from test_fileutilities import *
    from test_valuecalculator import *
    from test_formattingfunctions import *

if __name__ == "__main__":
    unittest.main()
