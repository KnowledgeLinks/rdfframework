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
import types
import logging

__author__ = "Mike Stabile, Jeremy Nelson"
__version__ = '0.0.38'

def package_modules(parent_module, registered=[]):
    parent_name = parent_module.__name__
    modules = [getattr(parent_module, module)
            for module in dir(parent_module)
            if isinstance(getattr(parent_module, module), types.ModuleType)
            and getattr(parent_module, module) not in registered
            and getattr(parent_module, module).__name__.startswith(parent_name)]
    registered += modules
    for module in modules:
        package_modules(module, registered)
    return registered

def set_module_loggers(modules, method="dummy"):
    for module in modules:
        if method == "dummy":
            logger = rdfframework.utilities.DummyLogger
        else:
            logger = logging.getLogger(module.__name__)
        setattr(module, "log", logger)
        logger.disabled = False

__modules__ = package_modules(rdfframework)

def configure_logging(modules, method="dummy"):
    # try:
    from .loggingsetup import LOGGING
    import logging.config
    logging.config.dictConfig(LOGGING)
    # except:
    #     pass
    set_module_loggers(modules, method)

configure_logging(__modules__, "active")
