''' Base class for reading and pushing to eslasticsearch'''
    
__author__="Mike Stabile, Jeremy Nelson"
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

MODULE_NAME = "%s.%s" % \
        (os.path.basename(os.path.split(inspect.stack()[0][1])[0]),
         os.path.basename(inspect.stack()[0][1]))


pp = pprint

MAPPINGS = json.loads(requests.get('http://localhost:9200/_mapping').text)


class EsBase():
    ''' Base elasticsearch rdfframework class for common es operations'''
        
    ln = "%s:EsBase" % MODULE_NAME
    log_level = logging.DEBUG
        
    def __init__(self, **kwargs):
        self.es_url = kwargs.get('es_url', 'http://localhost:9200')
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
            action = get_es_action_item(item, action_settings, doc_type, id_field)
            action_list.append(action)
        return action_list
               
    def bulk_save(self, action_list, **kwargs):
        ''' sends a passed in action_list to elasticsearch '''
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
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
        lg.info("Results\n%s", result)
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
        return result
        
    def get_list(self, method="search", **kwargs):
        """ returns a key value list of items based on the specfied criteria 
        
        """

        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        args = inspect.getargvalues(inspect.currentframe())[3]
        lg.debug("\n****** Args *****:\n%s",
                 pp.pformat(args))
        
        es = kwargs.get("es",self.es)
        doc_type = get2(kwargs, "doc_type", self.doc_type)
        fields = get2(kwargs, "fields")
        search_flds = kwargs.get("search_flds")
        sort_dir = get2(kwargs,"sort_dir", "asc")
        sort_fields = get2(kwargs,"sort_fields", get2(kwargs, "fields", []))
        size = get2(kwargs,"size",10)
        term = get2(kwargs,"term",'').replace("/","//")
        filter_field = kwargs.get('filter_field')
        filter_value = kwargs.get('filter_value')
        highlight = kwargs.get('highlight',False)
        from_ = kwargs.get('from_')
        dsl = {}
        # set retutn to only return the fields specified or return the whole
        # document if not specified
        if fields is not None:
            dsl["_source"] = fields
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
                search_term = "*%s*" % term.replace("(", "")
            elif term.startswith("<") and term.endswith(">"):
                search_term = term
            else:
                search_term = "*%s*" % term
            if search_flds is not None and len(search_flds) > 0:
                fields_to_search = search_flds
            elif len(fields) > 0:
                fields_to_search = fields
            else:
                fields_to_search = []
            dsl['query'] =  {
                "bool": {
                    "should": [
                        {
                            "query_string" : {
                                "query": search_term,
                                "analyzer": "default",
                                "analyze_wildcard": True
                            }                       
                        },
                        {
                            "query_string" : {
                                "query": search_term,
                                "analyzer": "default",
                                "analyze_wildcard": True,
                                "fields": fields_to_search,
                                "boost": 10
                            }
                        }
                    ]
                }  
            }
        else:
            dsl['query'] = {'bool':{}}
        if filter_value:
            path = '%s/%s' % (self.es_index, doc_type)
            filter_types = make_list(MAPS[path].get(filter_field))
            fld_filterable = \
                    len(set(['keyword','lower']).intersection(set(filter_types)))\
                     > 0
            if fld_filterable:
                if filter_types[0] == 'text':
                    filter_field = "%s.%s" % (filter_field, filter_types[1])
            else:
                return {'error': 
                        "Field %s is not filterable. Use a field that has 'keyword' or 'lower' as a mapping" % filter_field}
            dsl['query']['bool']['filter'] = {
                "term": { filter_field: filter_value }
            }
        # pdb.set_trace()
        if highlight is not None:
            dsl['highlight'] = {"fields": {"rdfs_label":{}}}
        lg.info("\n-------- size: %s\ndsl:\n%s", size, json.dumps(dsl,indent=4))

        result = es.search(index=self.es_index,
                           size=size,
                           from_=from_,
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
            refomated results list with calculation added to the '_calc' field
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
                item['_calc'] = "".join(calc_parts)
                pdb.set_trace()
        lg.debug("calc %s", calc)
        return results    

class IsFirst():
    ''' tracks if is the first time through a loop. class must be initialized
        outside the loop.
        
        *args:
            true -> specifiy the value to return on true
            false -> specify to value to return on false    '''
            
    def __init__(self):
        self.__first = True
        
    def first(self, true=True, false=False):
        if self.__first == True:
            self.__first = False
            return true
        else:
            return false

def get2(item, key, if_none=None, strict=True):
    ''' similar to dict.get functionality but None value will return then 
        if_none value 
     
    args:
        item: dictionary to search
        key: the dictionary key
        if_none: the value to return if None is passed in
        strict: if False an empty string is treated as None'''
        
    if not strict and item.get(key) == "":
        return if_none
    elif item.get(key) is None:
        return if_none
    else:
        return item.get(key)

class Dot(object):
    """ Takes a dictionary and gets and sets values via a "." dot notation
    of the path
    
    args:
        dictionary: The dictionary object
        copy_dict: Boolean - True - (default) does a deepcopy of the dictionay 
            before returning. False - maniplutes the passed in dictionary
            
    """
    def __init__(self, dictionary, copy_dict=True):
        self.obj = dictionary
        self.new_dict = {}
        self.copy_dict = copy_dict

    def get(self, prop):
        """ get the value off the passed in dot notation
        
        args:
            prop: a string of the property to retreive 
                "a.b.c" ~ dictionary['a']['b']['c']
        """
        prop_parts = prop.split(".")
        val = None
        for part in prop_parts:
            if val is None:
                val = self.obj.get(part)
            else:
                val = val.get(part)
        return val

    def set(self, prop, value):
        """ sets the dot notated property to the passed in value
        
        args:
            prop: a string of the property to retreive 
                "a.b.c" ~ dictionary['a']['b']['c']
            value: the value to set the prop object
        """
        
        prop_parts = prop.split(".")
        if self.copy_dict:
            new_dict = copy.deepcopy(self.obj)
        else:
            new_dict = self.obj
        pointer = None
        parts_length = len(prop_parts) - 1
        for i, part in enumerate(prop_parts):
            if pointer is None and i == parts_length:
                new_dict[part] = value
            elif pointer is None:
                pointer = new_dict.get(part)            
            elif i == parts_length:
                pointer[part] = value
            else:
                pointer = pointer.get(part)
        return new_dict

def get_es_action_item(data_item, action_settings, es_type, id_field=None):
    ''' This method will return an item formated and ready to append 
        to the action list '''
        
    action_item = dict.copy(action_settings)
    if id_field is not None:
        id_val = first(list(get_dict_key(data_item, id_field)))
        if id_val is not None:
            action_item['_id'] = id_val
    elif data_item.get('id'):
        if data_item['id'].startswith("%s/" % action_settings['_index']):
            action_item['_id'] = "/".join(data_item['id'].split("/")[2:])
        else:
            action_item['_id'] = data_item['id']
    if data_item.get('data'):
        action_item['_source'] = data_item['data']
    else:
        action_item['_source'] = data_item
    action_item['_type'] = es_type
    return action_item

def first(data):
    ''' returns the first item in a list and None if the list is empty '''
    
    data_list = make_list(data)
    if len(data_list) > 0:
        return data_list[0]
    else:
        return None

def make_list(value):
    ''' Takes a value and turns it into a list if it is not one

    !!!!! This is important becouse list(value) if perfomed on an
    dictionary will return the keys of the dictionary in a list and not
    the dictionay as an element in the list. i.e.
        x = {"first":1, "second":2}
        list(x) = ["first", "second"]
        or use this [x,]
        make_list(x) =[{"first":1, "second":2}]
    '''
    if not isinstance(value, list):
        value = [value]
    return value

def mapping_ref():
    es_mappings = \
            json.loads(requests.get('http://localhost:9200/_mapping').text)
    es_mappings = {"_".join(key.split("_")[:-1]): value['mappings'] \
                   for key, value in es_mappings.items()}

    new_map = {}
    for key, value in es_mappings.items():
        for sub_key, sub_value in value.items():
            new_map["/".join([key, sub_key])] = mapping_fields(sub_value['properties'
            ])
    return new_map

def mapping_fields(mapping, parent=[]):
    # rtn_list = []
    # for key, value in mapping.items():
    #     new_key = parent + [key]
    #     new_key = ".".join(new_key)
    #     rtn_list.append((new_key, value.get('type')))
    #     if value.get('properties'):
    #         rtn_list += mapping_fields(value['properties'], [new_key])
    #     elif value.get('fields'):
    #         rtn_list += mapping_fields(value['fields'], [new_key])
    # return rtn_list
    rtn_obj = {}
    for key, value in mapping.items():
        new_key = parent + [key]
        new_key = ".".join(new_key)
        rtn_obj.update({new_key: value.get('type')})
        if value.get('properties'):
            rtn_obj.update(mapping_fields(value['properties'], [new_key]))
        elif value.get('fields'):
            rtn_obj.update(mapping_fields(value['fields'], [new_key]))
            rtn_obj[new_key] = [rtn_obj[new_key]] + list(value['fields'].keys())
    return rtn_obj

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

def sample_data_convert(data, es_index, doc_type):
    if data.get('hits'):
        new_data = data['hits']['hits'][0]['_source']
    elif data.get('_source'):
        new_data = data['_source']
    conv_data = key_data_map(new_data, MAPS["%s/%s" % (es_index, doc_type)])
    conv_data = [(key, str(value['mapping']), str(value['data']),) \
                 for key, value in conv_data.items()]
    conv_data.sort(key=lambda tup: es_field_sort(tup[0]))
    return conv_data

MAPS = mapping_ref()

def sample_data_map():

    maps = MAPS
    rtn_obj = {}
    for path, mapping in maps.items():
        url = "/".join(['http://localhost:9200', path, '_search'])
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