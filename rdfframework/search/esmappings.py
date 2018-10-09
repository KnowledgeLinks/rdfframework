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
    log_level = logging.INFO

    es_mapping = None
    # es_settings = None

    def __init__(self, conn=None, **kwargs):
        if not conn:
            conn = CFG.conns.search
        self.conn = conn
        self.es_url = conn.es_url
        self.es = conn.es
        self.mapping_url = '{0}/_mapping'.format(self.es_url)

    @staticmethod
    def list_mapped_classes():
        """
        Returns all the rdfclasses that have and associated elasticsearch
        mapping

        Args:
            None

        """
        cls_dict = {key: value
                    for key, value in MODULE.rdfclass.__dict__.items()
                    if not isinstance(value, RdfConfigManager)
                    and key not in ['properties']
                    and hasattr(value, 'es_defs')
                    and value.es_defs.get('kds_esIndex')}
        new_dict = {}
        # remove items that are appearing as a subclass of a main mapping class
        # the intersion of the set of the cls_dict values and the a classes
        # individual hierarchy will be >1 if the class is a subclass of another
        # class in the list
        potential_maps = set([cls_.__name__ for cls_ in cls_dict.values()])
        for name, cls_ in cls_dict.items():
            parents = set(cls_.hierarchy)
            if len(parents.intersection(potential_maps)) <= 1:
                new_dict[name] = cls_
        return new_dict

    @classmethod
    def list_indexes(cls):
        """
        Returns a dictionary with the key as the es_index name and the
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
        """
        Returns an elasticsearch mapping for the specified index based off
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
                    # "read_only_allow_delete": False,
                    "index": {
                        # "blocks" : {
                        #     "read_only_allow_delete" : "false"
                        # },
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
        }

        for idx_cls in idx_obj[idx_name]:
            # pdb.set_trace()
            es_map['body']['mappings'][idx_cls.es_defs['kds_esDocType'][0]] = \
                    {'properties': idx_cls.es_mapping(idx_cls)}

        return es_map

    def send_es_mapping(self, es_map, **kwargs):
        """
        sends the mapping to elasticsearch

        args:
            es_map: dictionary of the index mapping

        kwargs:
            reset_idx: WARNING! If True the current referenced es index
                    will be deleted destroying all data in that index in
                    elasticsearch. if False an incremented index will be
                    created and data-migration will start from the old to
                    the new index
        """
        log.setLevel(kwargs.get('log_level', self.log_level))

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
            log.warning("DELETING Elasticsearch INDEX => %s ******", alias)
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
            self.es.indices.delete_alias(index=idx_names['old'],
                                         name=alias,
                                         ignore=[403])
            self.es.indices.delete(index=idx_names['old'], ignore=[400, 404])
        # add the alias to the new index
        self.es.indices.put_alias(index=idx_names['new'], name=alias)


    def initialize_indices(self, **kwargs):
        """
        creates all the indicies that are defined in the rdf definitions

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

    def get_es_mappings(self):
        """
        Returns the mapping defitions presetn in elasticsearh
        """

        es_mappings = json.loads(requests.get(self.mapping_url).text)
        es_mappings = {"_".join(key.split("_")[:-1]): value['mappings'] \
                       for key, value in es_mappings.items()}
        return es_mappings

    def mapping_ref(self, es_mappings):
        """
        Retruns a dictionary of mappings and the fiels names in dot notation

        args:
            mappings: es mapping defitions to parse
        """

        new_map = {}
        for key, value in es_mappings.items():
            for sub_key, sub_value in value.items():
                new_map["/".join([key, sub_key])] = \
                        mapping_fields(sub_value['properties'])
        return new_map

    def key_data_map(source, mapping, parent=[]):
        rtn_obj = {}
        if isinstance(source, dict):
            for key, value in source.items():

                new_key = parent + [key]
                new_key = ".".join(new_key)
                rtn_obj.update({new_key: {'mapping':mapping.get(new_key)}})
                if isinstance(value, list):
                    value = value[0]
                    rtn_obj.update(key_data_map(value, mapping, [new_key]))
                    if isinstance(value, dict):
                        rtn_obj[new_key]['data'] = "%s ...}" % str(value)[:60]
                elif isinstance(value, dict):
                    rtn_obj.update(key_data_map(value, mapping, [new_key]))
                    rtn_obj[new_key]['data'] = "%s ...}" % str(value)[:60]
                else:
                    rtn_obj[new_key]['data'] = value
        elif isinstance(source, list):
            rtn_obj.update(key_data_map(value[0], mapping, parent))
        else:
            rtn_obj = {"".join(parent): {'data':source,
                                         'mapping':mapping.get("".join(parent))}}
            # pdb.set_trace()
        return rtn_obj

    def sample_data_convert(es_url, data, es_index, doc_type):
        maps = self.mapping_ref(self.get_es_mappings())
        if data.get('hits'):
            new_data = data['hits']['hits'][0]['_source']
        elif data.get('_source'):
            new_data = data['_source']
        conv_data = key_data_map(new_data, maps["%s/%s" % (es_index, doc_type)])
        conv_data = [(key, str(value['mapping']), str(value['data']),) \
                     for key, value in conv_data.items()]
        conv_data.sort(key=lambda tup: es_field_sort(tup[0]))
        return conv_data

    def sample_data_map(es_url):

        maps = mapping_ref(es_url)
        rtn_obj = {}
        for path, mapping in maps.items():
            url = "/".join(["{}:9200".format(es_url), path, '_search'])
            sample_data = json.loads(requests.get(url).text)
            sample_data = sample_data['hits']['hits'][0]['_source']
            conv_data = key_data_map(sample_data, mapping)

            rtn_obj[path] = [(key, str(value['mapping']), str(value['data']),) \
                             for key, value in conv_data.items()]
            rtn_obj[path].sort(key=lambda tup: es_field_sort(tup[0]))
        return rtn_obj

    def es_field_sort(fld_name):
        """ Used with lambda to sort fields """
        parts = fld_name.split(".")
        if "_" not in parts[-1]:
            parts[-1] = "_" + parts[-1]
        return ".".join(parts)

def mapping_fields(mapping, parent=[]):
    """
    reads an elasticsearh mapping dictionary and returns a list of fields
    cojoined with a dot notation

    args:
        obj: the dictionary to parse
        parent: name for a parent key. used with a recursive call
    """
    rtn_obj = {}
    for key, value in mapping.items():
        new_key = parent + [key]
        new_key = ".".join(new_key)
        rtn_obj.update({new_key: value.get('type')})
        if value.get('properties'):
            rtn_obj.update(mapping_fields(value['properties'], [new_key]))
        elif value.get('fields'):
            rtn_obj.update(mapping_fields(value['fields'], [new_key]))
            rtn_obj[new_key] = [rtn_obj[new_key]] + \
                    list(value['fields'].keys())
    return rtn_obj

def dict_fields(obj, parent=[]):
    """
    reads a dictionary and returns a list of fields cojoined with a dot
    notation

    args:
        obj: the dictionary to parse
        parent: name for a parent key. used with a recursive call
    """
    rtn_obj = {}
    for key, value in obj.items():
        new_key = parent + [key]
        new_key = ".".join(new_key)
        if isinstance(value, list):
            if value:
                value = value[0]
        if isinstance(value, dict):
            rtn_obj.update(dict_fields(value, [new_key]))
        else:
            rtn_obj.update({new_key: value})
    return rtn_obj
