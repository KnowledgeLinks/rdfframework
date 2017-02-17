"""	This module is used for setting an intial test configs and values for 
the rdfframework """

import sys
import os

PACKAGE_BASE = os.path.abspath(
    os.path.split(
        os.path.dirname(__file__))[0])
print("PACKAGE_BASE: ", PACKAGE_BASE)
sys.path.append(PACKAGE_BASE)

from testconfig import config

from rdfframework.getframework import fw_config as fwc, get_framework as fw
from rdfframework.utilities import DictClass, pp, get_ns_obj

print("CONFIG ---------------------------------------------------------------")
pp.pprint(DictClass(config))
print("----------------------------------------------------------------------")
#fw(config=config, root_file_path=PACKAGE_BASE)
NSM = get_ns_obj(config=DictClass(config))

	