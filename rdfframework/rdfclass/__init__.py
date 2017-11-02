__author__ = "Mike Stabile, Jeremy Nelson"

"""
rdfclass
========

RDFframework is a flexible application framework for implementing an
application defined in a Resource Description Framework (RDF) data file that
is based on the http://knowledgelinks.io/ns/data-structures/ (kds) RDF
vocabulary.

:copyright: Copyright (c) 2016 by Michael Stabile and Jeremy Nelson.
:license: To be determined, see LICENSE.txt for details.
"""

from .rdfproperty import make_property, RdfPropertyMeta, properties, \
                         domain_props, link_property
from .rdfclass import RdfClassBase, RdfClassMeta, remove_parents, list_hierarchy
# from .rdfclassgenerator import RdfClassGenerator
from .rdffactories import RdfClassFactory, RdfPropertyFactory

__version__ = '0.0.1'
