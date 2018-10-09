''' Base class for reading and pushing to eslasticsearch'''

__author__="Mike Stabile, contact @ mstabile75@gmail.com"
import sys
import os
import inspect
import logging
import csv
import pdb
import argparse
import requests
import json
import pprint

from elasticsearch import Elasticsearch, helpers
from rdfframework.utilities import IsFirst, get2, Dot
from rdfframework.search import get_es_action_item, EsMappings
from rdfframework.configuration import RdfConfigManager

MODULE_NAME = "%s.%s" % \
        (os.path.basename(os.path.split(inspect.stack()[0][1])[0]),
         os.path.basename(inspect.stack()[0][1]))

config = RdfConfigManager()



class EsBase():
    ''' Base elasticsearch rdfframework class for common es operations'''

    ln = "%s:EsBase" % MODULE_NAME
    log_level = logging.INFO

    def __init__(self, **kwargs):
        self.es_url = kwargs.get('es_url', config.ES_URL)
        self.es = kwargs.get("es",Elasticsearch([self.es_url]))
        self.op_type = kwargs.get("op_type", "index")
        self.es_index = kwargs.get("es_index")
        self.doc_type = kwargs.get("doc_type")
        self.reset_index = kwargs.get("reset_index",False)
        self.reset_doc_type = kwargs.get("reset_doc_type",False)
        self.es_mapping = kwargs.get("es_mapping")


    def make_action_list(self, item_list, **kwargs):
        ''' Generates a list of actions for sending to Elasticsearch '''

        action_list = []
        es_index = get2(kwargs, "es_index", self.es_index)
        action_type = kwargs.get("action_type","index")
        action_settings = {'_op_type': action_type,
                           '_index': es_index}
        doc_type = kwargs.get("doc_type", self.doc_type)
        if not doc_type:
            doc_type = "unk"
        id_field = kwargs.get("id_field")
        for item in item_list:
            action = get_es_action_item(item,
                                        action_settings,
                                        doc_type,
                                        id_field)
            action_list.append(action)
        return action_list

    def bulk_save(self, action_list, **kwargs):
        ''' sends a passed in action_list to elasticsearch '''

        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        err_log = logging.getLogger("index.errors")
        es = self.es
        es_index = get2(kwargs, "es_index", self.es_index)
        reset_index = kwargs.get("reset_index",self.reset_index)
        doc_type = kwargs.get("doc_type", self.doc_type)

        lg.info("Sending %s items to Elasticsearch",len(action_list))
        # bulk_stream = helpers.streaming_bulk(es,
        result = helpers.bulk(es,
                              action_list,
                              chunk_size=400,
                              raise_on_error=False)
        lg.info("FINISHED sending to Elasticsearch")
        if result[1]:
            lg.info("Formating Error results")
            # action_keys = {item['_id']:i for i, item in enumerate(action_list)}
            new_result = []
            for item in result[1][:5]:
                for action_item in action_list:
                    if action_item['_id'] == item[list(item)[0]]['_id']:
                        new_result.append((item, action_item,))
                        break
            err_log.info("Results for batch '%s'\n(%s,\n%s\n%s)",
                         kwargs.get('batch', "No Batch Number provided"),
                         result[0],
                         json.dumps(new_result, indent=4),
                         json.dumps(result[1]))
            del new_result
            lg.info("Finished Error logging")
        # for success, result in bulk_stream:
        #     lg.debug("\nsuccess: %s \nresult:\n%s", success, pp.pformat(result))
        return result

    def save(self, data, **kwargs):
        """ sends a passed in action_list to elasticsearch

        args:
            data: that data dictionary to save

        kwargs:
            id: es id to use / None = auto
            """

        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)

        es = self.es
        es_index = get2(kwargs, "es_index", self.es_index)
        reset_index = kwargs.get("reset_index",self.reset_index)
        doc_type = kwargs.get("doc_type", self.doc_type)
        op_type = kwargs.get("op_type", self.op_type)
        id_value = kwargs.get("id")
        id_field = kwargs.get("id_field")
        if id_field:
            id_value = data.get(id_field)
        if op_type == "index":
            result = es.index(index=es_index,
                               id=id_value,
                               doc_type=doc_type,
                               body=data)
        elif op_type == "create":
            result = es.create(index=es_index,
                               id=id_value,
                               doc_type=doc_type,
                               body=data)

        lg.debug("Result = \n%s",pp.pformat(result))
        return result

    def _find_ids(self,
                  data_list,
                  prop,
                  lookup_index,
                  lookup_doc_type,
                  lookup_field):
        """ Reads a list of data and replaces the ids with es id of the item

        args:
            data_list: list of items to find in replace
            prop: full prop name in es format i.e. make.id
            lookup_src: dictionary with index doc_type ie.
                {"es_index": "reference", "doc_type": "device_make"}
            lookup_fld: field to do the lookup against in full es naming
                convention i.e. make.raw
        """
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)

        rtn_list = []
        first_time = IsFirst()
        for item in data_list:
            # the Dot class will retive and set dictionary values via dot
            # notation
            val = Dot(item).get(prop)
            if val.startswith("#;lookup#;"):
                lookup_val = val.replace("#;lookup#;", "")
                lookup_obj = self.get_item(lookup_val, lookup_field)
                if first_time.first():
                    lg.debug("  lookup_obj:\n%s", pp.pformat(lookup_obj))
                if lookup_obj:
                    rtn_list.append(Dot(item).set(prop, lookup_obj['_id']))
        return rtn_list

    def get_doc(self, item_id, id_field="_id", **kwargs):
        """ returns a single item data record/document based on specified
        criteria

        args:
            item_id: the id value of the desired item. Can be used in
                     combination with the id_field for a paired lookup.
            id_field: the field that is related to the item_id; default = '_id'
                      **Example**: selecting a country using a different
                      itendifier than the record id. The United States's '_id'
                      value is 'US' however the record can be found by
                      specifying item_id='USA', id_field='ISO 3166-1 A3'
        kwargs:
            used to overided any of the initialization values for the class
        """

        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)

        args = inspect.getargvalues(inspect.currentframe())[3]
        lg.debug("\n****** Args *****:\n%s",
                 pp.pformat(args))

        es = kwargs.get("es",self.es)
        doc_type = kwargs.get("doc_type", self.doc_type)
        if id_field == "_id":
            lg.debug("*** _id lookup: index: %s item_id: %s",
                     self.es_index,
                     item_id)
            result = es.get(index=self.es_index,
                            id=item_id)
        else:
            dsl = {
                "query": {
                    "constant_score": {
                        "filter": {
                            "term": { id_field: item_id }
                        }
                    }
                }
            }
            lg.debug("*** id_field lookup: index: %s item_id: %s \nDSL: %s",
                     self.es_index,
                     item_id,
                     pp.pformat(dsl))
            result = es.search(index=self.es_index,
                               doc_type=doc_type,
                               body=dsl)
            result = first(result.get("hits",{}).get("hits",[]))
        lg.debug("\tresult:\n%s", pp.pformat(result))
        self.item_data = result
        self.form_data = MultiDict(result)
        return result

    def get_list(self, method="list", **kwargs):
        """ returns a key value list of items based on the specfied criteria

        """

        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)

        args = inspect.getargvalues(inspect.currentframe())[3]
        lg.debug("\n****** Args *****:\n%s",
                 pp.pformat(args))

        es = kwargs.get("es",self.es)
        doc_type = get2(kwargs, "doc_type", self.doc_type)
        id_field = get2(kwargs, "id_field", "_id")
        value_fld = kwargs.get("value_fld")
        fields = kwargs.get("fields")
        sort_dir = get2(kwargs,"sort_dir", "asc")
        sort_fields = get2(kwargs,"sort_fields", get2(kwargs, "fields", [value_fld]))
        size = get2(kwargs,"size",2000)
        term = get2(kwargs,"term",'').replace("/","//")
        filter_field = kwargs.get('filter_field')
        filter_value = kwargs.get('filter_value')
        dsl = {}
        # set retutn to only return the fields specified or return the whole
        # document if not specified
        if fields is not None:
            dsl["_source"] = fields
        elif value_fld is not None:
            dsl["_source"] = [value_fld]
            fields = [value_fld]
        else:
            fields = []
        # set query parameters based on the return method "list" or "search"
        if sort_dir != "none" and method == "list":
            dsl["sort"] = []
            for fld in sort_fields:
                if fld is not None:
                    dsl["sort"].append({ fld: sort_dir })
        if method == "search":
            # query in elasticsearch breaks if the is a single open parenthesis
            # remove a single parenthesis from the search term
            if "(" in term and ")" not in term:
                search_term = term.replace("(", "")
            else:
                search_term = term
            size = 5
            dsl['query'] =  {
                "bool": {
                    "should": [
                        {
                            "query_string" : {
                                "analyze_wildcard": {
                                    "query": "*%s*" % search_term
                                }

                            }
                        },
                        {
                            "query_string" : {
                                "query": "*%s*" % search_term,
                                "analyzer": "default",
                                "analyze_wildcard": True,
                                "fields": fields,
                                "boost": 10
                            }
                        }
                    ]
                }
            }
        else:
            pass
        if filter_value:
            dsl['filter'] = {
                "term": { filter_field: filter_value }
            }
        lg.info("\n-------- size: %s\ndsl:\n%s", size, json.dumps(dsl,indent=4))
        result = es.search(index=self.es_index,
                           size=size,
                           doc_type=doc_type,
                           body=dsl)
        if kwargs.get("calc"):
            result = self._calc_result(result, kwargs['calc'])
        lg.debug(pp.pformat(result))
        return result

    def _calc_result(self, results, calc):
        """ parses the calc string and then reads the results and returns
        the new value Elasticsearch no longer allow dynamic in scripting

        args:
            results: the list of results from Elasticsearch
            calc: the calculation sting

        returns:
            refomated results list with calculation added to the '__calc' field
            in _source

        examples:
            concatenation: use + field_names and double quotes to add text
                fld1 +", " + fld2 = "fld1, fld2"
        """
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        # if the calculation is empty exit
        if calc is None:
            return results
        lg.debug("calc %s", calc)
        # perform concatenation
        hits = results.get('hits',{}).get('hits',[])
        for item in hits:
            lg.debug("\n*** item:\n%s", pp.pformat(item))
            if "+" in calc:
                calc_parts = calc.split("+")
                calc_str = ""
                for i, part in enumerate(calc_parts):
                    if '"' in part:
                        calc_parts[i] = part.replace('"','')
                    else:
                        if part.startswith("_"):
                            calc_parts[i] = item.get(part)
                        else:
                            calc_parts[i] = Dot(item['_source']).get(part)
                lg.debug(" calc result: %s", "".join(calc_parts))
                item['_source']['__calc'] = "".join(calc_parts)
        lg.debug("calc %s", calc)
        return results
