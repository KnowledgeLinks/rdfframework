"""
RDFframework
=======

RDFframework is a flexible application framework for implementing an
application defined in a Resource Description Framework (RDF) data file that
is based on the http://knowledgelinks.io/ns/data-structures/ (kds) RDF
vocabulary.

:copyright: Copyright (c) 2016 by Michael Stabile and Jeremy Nelson.
:license: To be determined, see LICENSE.txt for details.
"""

# import rdfframework.rdfclass
# from .rdfdatasets import RdfDataset
from .framework import RdfFramework

import rdfframework.utilities
import rdfframework.connections
import rdfframework.datamergers
import rdfframework.configuration
import rdfframework.search
import rdfframework.sparql
import rdfframework.rml
import rdfframework.datamanager
import rdfframework.datasets

__author__ = "Mike Stabile, Jeremy Nelson"
__version__ = '0.0.21'
