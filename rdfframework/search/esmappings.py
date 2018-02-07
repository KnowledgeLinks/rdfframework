""" Class for getting data mappings"""

__author__="Mike Stabile, Jeremy Nelson"
import os
import inspect
import logging
import json
import requests
import pdb
import elasticsearch.exceptions as es_except

from rdfframework.utilities import pp
from rdfframework.configuration import RdfConfigManager
# from rdfframework.rdfclass import rdfclass
from elasticsearch import Elasticsearch

MODULE_NAME = "%s.%s" % \
        (os.path.basename(os.path.split(inspect.stack()[0][1])[0]),
         os.path.basename(inspect.stack()[0][1]))
MODULE = __import__(__name__)
CFG = RdfConfigManager()

class EsMappings():
    """ Class for manipulating elasticsearch mappings with the rdfframework

    attributes:

    """
    # setup logging for class
    ln = "%s:EsMapping" % MODULE_NAME
    log_level = logging.INFO

    es_mapping = None
    es_settings = None

    def __init__(self, **kwargs):
        self.es_url = kwargs.get('es_url',
                                 CFG.get('ES_URL','http://localhost:9200'))
        self.es = kwargs.get("es",Elasticsearch([self.es_url]))

    @staticmethod
    def list_mapped_classes():
        """ Returns all the rdfclasses that have and associated elasticsearch
            mapping

            Args:
                None

        """
        return {key: value for key, value in MODULE.rdfclass.__dict__.items() \
                if not isinstance(value, RdfConfigManager) \
                and hasattr(value, 'es_defs') \
                and value.es_defs.get('kds_esIndex')}

    @classmethod
    def list_indexes(cls):
        """ Returns a dictionary with the key as the es_index name and the
            object is a list of rdfclasses for that index

            args:
                None
        """

        cls_list = cls.list_mapped_classes()
        rtn_obj = {}
        for key, value in cls_list.items():
            idx = value.es_defs.get('kds_esIndex')[0]
            try:
                rtn_obj[idx].append(value)
            except KeyError:
                rtn_obj[idx] = [value]
        return rtn_obj

    @classmethod
    def get_rdf_es_idx_map(cls, idx_obj):
        """ Returns an elasticsearch mapping for the specified index based off
            of the mapping defined by rdf class definitions

            args:
                idx_obj: Dictionary of the index and a list of rdfclasses
                         included in the mapping
        """
        idx_name = list(idx_obj)[0]

        es_map = {
            "index": idx_name,
            "body" : {
                "mappings": {},
                "settings": {
                    "analysis": {
                        "analyzer": {
                            "keylower": {
                                "tokenizer": "keyword",
                                "type": "custom",
                                "filter": "lowercase",
                                "ignore_above" : 256
                            }
                        }
                    }
                }
            }
        }

        for idx_cls in idx_obj[idx_name]:
            es_map['body']['mappings'][idx_cls.es_defs['kds_esDocType'][0]] = \
                    {'properties': idx_cls.es_mapping(idx_cls)}

        return es_map

    def send_es_mapping(self, es_map, **kwargs):
        """ sends the mapping to elasticsearch

            args:
                es_map: dictionary of the index mapping

            kwargs:
                reset_idx: WARNING! If True the current referenced es index
                        will be deleted destroying all data in that index in
                        elasticsearch. if False an incremented index will be
                        created and data-migration will start from the old to
                        the new index
        """
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)

        def next_es_index_version(curr_alias):
            """ returns the next number for a new index

                args:
                    alias_def: the dictionary returned by es for get alias
            """
            try:
                alias_def = self.es.indices.get_alias(alias)
            except es_except.NotFoundError:
                alias_def = {alias + "_v0":{}}
            old_idx = list(alias_def)[0]
            parts = old_idx.split("_v")
            try:
                parts[1] = str(int(parts[1]) + 1)
            except IndexError:
                parts = [old_idx,'1']
            return {'old': old_idx, 'new': "_v".join(parts)}

        reset_idx= kwargs.get('reset_idx', False)
        alias = es_map.pop('index')
        idx_names = next_es_index_version(alias)

        # Delete if the index series if reset_idx was passed
        if reset_idx:
            lg.warning("DELETING Elasticsearch INDEX => %s ******", alias)
            self.es.indices.delete(index=alias + "_v*", ignore=[400, 404])
            idx_names['new'] = alias + "_v1"

        # Create the new index and apply the mapping
        self.es.indices.create(index=idx_names['new'],
                               body=es_map['body'],
                               update_all_types=True)
        # if the index was not deleted transfer documents from old to the
        # new index
        if not reset_idx and self.es.indices.exists(idx_names['old']):
            url = os.path.join(self.es_url,'_reindex').replace('\\','/')
            data = {"source":{"index": idx_names['old']},
                    "dest":{"index": idx_names['new']}}
            # Python elasticsearch recommends using a direct call to the
            # es 5+ _reindex URL vice using their helper.
            result = requests.post(url,
                    headers={'Content-Type':'application/json'},
                    data = json.dumps(data))
            self.es.indices.delete_alias(index=idx_names['old'], name=alias)
            self.es.indices.delete(index=idx_names['old'], ignore=[400, 404])
        # add the alias to the new index
        self.es.indices.put_alias(index=idx_names['new'], name=alias)


    def initialize_indices(self, **kwargs):
        """ creates all the indicies that are defined in the rdf definitions

            kwargs:
                action: which action is to be perfomed
                        initialize: (default) tests to see if the index exisits
                                    if not creates it
                        reset: deletes all of the indexes and recreate them
                        update: starts a mapping update and reindexing process
        """
        action = kwargs.get('action', 'initialize')
        if action == 'update':
            kwargs['reset_idx'] = False
        elif action =='reset':
            kwargs['reset_idx'] = True

        idx_list = self.list_indexes()
        for idx, values in idx_list.items():
            if (action == 'initialize' and not self.es.indices.exists(idx)) \
                or action != 'initialize':
                self.send_es_mapping(self.get_rdf_es_idx_map({idx: values}),
                                     **kwargs)
