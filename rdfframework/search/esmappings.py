""" Class for getting data mappings"""
    
__author__="Mike Stabile, Jeremy Nelson"
import os
import inspect
import logging
import json

from rdfframework.utilities import pp

MODULE_NAME = "%s.%s" % \
        (os.path.basename(os.path.split(inspect.stack()[0][1])[0]),
         os.path.basename(inspect.stack()[0][1]))
         
class EsMappings():
    """ Takes and parses files from opengeocode.org and pushes them into 
    Elasticsearch 
    
    attributes:
        
    """
    # setup logging for class    
    ln = "%s:EsMapping" % MODULE_NAME
    log_level = logging.INFO
    
    es_mapping = None
    es_settings = None
            
    def __init__(self, **kwargs):
        pass
 
                 
    def get_mapping(self, es_index, doc_type=None):
        """ Retrieves the full mapping for for the specified index
        
        args:
            es_index: The elasticsearch index name
            doc_type: Optional document type. Returns the full index mapping
                if not supplied
        """
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        return None
        
    def get_es_mapping(self, es_index, doc_type=None):
        """ Retrieves the es mapping for for the specified index
        
        args:
            es_index: The elasticsearch index name
            doc_type: Optional document type. Returns the full index mapping
                if not supplied
        """
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        return None
    
    def get_es_settings(self, es_index, doc_type=None):
        """ Retrieves the es settings for for the specified index
        
        args:
            es_index: The elasticsearch index name
            doc_type: Optional document type. Returns the full index mapping
                if not supplied
        """
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(logging.DEBUG) #self.log_level)
        
        return None
