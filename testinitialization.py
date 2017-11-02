"""    This module is used for setting an intial test configs and values for
the rdfframework """

import pdb
import rdfframework.rdfclass

from testconfig import config
from rdfframework.rdfdatatypes import rdfdatatypes as rdt, BaseRdfDataType, Uri
from rdfframework.framework import RdfFramework
from rdfframework.rdfdatasets import RdfDataset

r = rdfframework.rdfclass

RdfFramework(reset=False, config=config)

