"""    This module is used for setting an intial test configs and values for
the rdfframework """

import pdb
import rdfframework.rdfclass

from testconfig import config
from rdfframework.rdfdatatypes import rdfdatatypes as rdt, BaseRdfDataType, Uri
from rdfframework.framework import RdfFramework
from rdfframework.rdfdatasets import RdfDataset
from rdfframework.configuration import RdfConfigManager
from rdfframework.sparql import get_all_item_data

r = rdfframework.rdfclass

RdfFramework(reset=False, config=config)

cfg = RdfConfigManager()

item_uri = "<http://library.kean.edu/173849#Work>"
conn = cfg.data_tstore
data = get_all_item_data(item_uri, conn)
x = RdfDataset(data, item_uri)
