__author__ = "Mike Stabile, Jeremy Nelson"

import os
import pdb
import pprint
import json
import types
import inspect
from hashlib import sha1


from rdfframework.utilities import RdfNsManager, render_without_request, \
                                   RdfConfigManager, make_list
from rdfframework.rdfdatatypes import BaseRdfDataType
from rdfframework.sparql import run_sparql_query
from rdfframework.rdfdatasets import RdfDataset
from rdfframework.rdfclass import RdfClassBase
from rdfframework import rdfclass
CFG = RdfConfigManager()
NSM = RdfNsManager()



class RdfClassGenerator(object):
    def __init__(self, reset=False, nsm=NSM, cfg=CFG):
        self.cfg = cfg
        self.nsm = nsm
        self.__get_defs(not reset)
        self.__make_defs()
        self.__make_classes()

    def __get_defs(self, cache=True):
        if cache:
            with open(
                os.path.join(self.cfg.JSON_LOCATION, "class_query.json")) as file_obj:
                self.cls_defs_results = json.loads(file_obj.read())
        else:
            sparqldefs = render_without_request("sparqlAllRDFClassDefs2.rq",
                                                graph=self.cfg.RDF_DEFINITION_GRAPH,
                                                prefix=self.nsm.prefix())
            print("Starting Class Def query")
            rdf_defs = self.cfg.RDF_DEFINITIONS
            self.cls_defs_results = run_sparql_query(sparqldefs,
                    namespace=rdf_defs.namespace)
            print("Ending Class Def Query")
            with open(
                os.path.join(self.cfg.JSON_LOCATION,"class_query.json"),
                "w") as file_obj:
                file_obj.write(json.dumps(self.cls_defs_results, indent=4) )

    def __make_defs(self):

        class_defs = {}
        for item in self.cls_defs_results:
            try:
                class_defs[item['RdfClass']['value']].append(item)
            except KeyError:
                class_defs[item['RdfClass']['value']] = [item]

        self.cls_defs = {self.nsm.pyuri(key):RdfDataset(value, def_load=True, bnode_only=True)
                         for key, value in class_defs.items()}
        self.cfg.__setattr__('rdf_class_defs', self.cls_defs, True)

    def __make_classes(self):
        # pdb.set_trace()
        # set the all the base classes
        created = []
        print("class len: ", len(self.cls_defs.keys()))
        for name, cls_defs in self.cls_defs.items():
            if not self.cls_defs[name][name].get('rdfs_subClassOf'):
                created.append(name)
                setattr(rdfclass,
                        name,
                        types.new_class(name,
                                        (RdfClassBase,),
                                        {#'metaclass': RdfClassMeta,
                                         'cls_defs': cls_defs}))
        for name in created:
            del self.cls_defs[name]
        left = len(self.cls_defs.keys())
        classes = []
        while left > 0:
            new = []
            for name, cls_defs in self.cls_defs.items():
                parents = self.cls_defs[name][name].get('rdfs_subClassOf')
                # pdb.set_trace()
                for parent in make_list(parents):
                    bases = tuple()
                    if parent in created or parent in classes:
                        if parent in classes:
                            bases += (RdfClassBase, )
                        else:
                            base = getattr(rdfclass, parent)
                            bases += (base,) + base.__bases__
                if len(bases) > 0:
                    created.append(name)
                    setattr(rdfclass,
                            name,
                            types.new_class(name,
                                            bases,
                                            {#'metaclass': RdfClassMeta,
                                             'cls_defs': cls_defs}))
            for name in created:
                try:
                    del self.cls_defs[name]
                except KeyError:
                    pass
            if left == len(self.cls_defs.keys()):
                c_list = [self.cls_defs[name][name].get('rdfs_subClassOf') \
                          for name in self.cls_defs.keys()]
                classess = []
                for cl in c_list:
                    for item in cl:
                        classes.append(item)

                for name in self.cls_defs.keys():
                    if name in classes:
                        classes.remove(name)
            left = len(self.cls_defs.keys())

# import re
# import json
# import requests
# import copy
# import pdb
# from werkzeug.datastructures import FileStorage
# from jinja2 import Template
# from hashlib import sha1
# #from rdfframework import fw_config
# try:
#     from rdfframework.utilities import clean_iri, iri, is_not_null, \
#         make_list, make_set, make_triple, remove_null, DeleteProperty, \
#         NotInFormClass, pp, uri, calculate_default_value, uri_prefix, nouri, \
#         pyuri, get_attr, slugify, RdfConfigManager
# except ImportError:
#     # Try local imports
#     from .utilities import clean_iri, iri, is_not_null, \
#         make_list, make_set, make_triple, remove_null, DeleteProperty, \
#         NotInFormClass, pp, uri, calculate_default_value, uri_prefix, nouri, \
#         pyuri, get_attr, slugify, RdfConfigManager
   

# from .getframework import get_framework as rdfw
# try:
#     from rdfframework.rdfdatatypes import BaseRdfDataType
#     from rdfframework.rdfdatatype import RdfDataType
#     from rdfframework.utilities.debug import dumpable_obj
#     from rdfframework.processors import clean_processors, run_processor
#     from rdfframework.sparql import save_file_to_repository
# except ImportError:
#     # Try local imports
#     from .rdfdatatype import RdfDataType
#     from .utilities.debug import dumpable_obj
#     from .processors import clean_processors, run_processor
#     from .sparql import save_file_to_repository
#     from .rdfdatatypes import BaseRdfDataType
   
# setting DEBUG to False will turn all the debug printing off in the module

# class RdfBaseClass(dict):
#     # _reserved = ['add_property',
#     #              '_format',
#     #              '_reserved',
#     #              '_subject',
#     #              '_type',
#     #              'to_json',
#     #              'uri_format',
#     #              'conv_json']

#     # __slots__ = ['_subject']

#     uri_format = 'sparql_uri'

#     def __init__(self, sub, **kwargs):
#         if isinstance(sub, dict):
#             self._subject = sub
#             self.add_property(sub['p'], sub['o'], kwargs.get("obj_method"))
#         else:
#             self._subject = {"s":sub, "p":None, "o":None}
            

#     def add_property(self, pred, obj, obj_method=None):
#         try:
#             self[pred].append(obj)
#         except AttributeError:
#             new_list = [self[pred]]
#             new_list.append(obj)
#             self[pred] = new_list
#         except KeyError:
#             if obj_method != "list":
#                 self[pred] = obj
#             else:
#                 self[pred] = [obj]

#     @property
#     def to_json(self, start=True):
#         return self.conv_json(self.uri_format)

#     def conv_json(self, uri_format="sparql_uri", add_ids=False):

#         def convert_item(ivalue):
#             nvalue = ivalue
#             if isinstance(ivalue, BaseRdfDataType):
#                 if ivalue.type == 'uri':
#                     if ivalue.startswith("pyuri") and uri_format == "pyuri":
#                         nvalue = getattr(ivalue, "sparql")
#                     else:
#                         nvalue = getattr(ivalue, uri_format)
#                 else:
#                     nvalue = ivalue.to_json
#             elif isinstance(ivalue, RdfBaseClass):
#                 if ivalue._subject['s'].type == "uri":
#                     # nvalue = getattr(ivalue._subject['s'], uri_format)
#                     nvalue = ivalue.conv_json(uri_format, add_ids)
#                 elif ivalue._subject['s'].type == "bnode":
#                     nvalue = ivalue.conv_json(uri_format, add_ids)
#             elif isinstance(ivalue, list):
#                 nvalue = []
#                 for item in ivalue:
#                     temp = convert_item(item)
#                     nvalue.append(temp)
#             return nvalue

#         rtn_val = {key: convert_item(value) for key, value in self.items()}
#         #pdb.set_trace()
#         if add_ids:
            
#             if self._subject['s'].type == 'uri':
#                 rtn_val['uri'] = self._subject['s'].sparql_uri
#                 rtn_val['id'] = sha1(rtn_val['uri'].encode()).hexdigest()
#         #return {key: convert_item(value) for key, value in self.items()}
#         return rtn_val

# DEBUG = True
# class RdfClass(object):
#     ''' RDF Class for an RDF Class object.
#         Used for manipulating and validating an RDF Class subject'''


#     def __init__(self, json_obj, class_name, **kwargs):
#         if not DEBUG:
#             debug = False
#         else:
#             debug = False
#         if debug: print("\nSTART RdfClass.init ---------------------------\n")
#         self.class_name = None
#         self.kds_properties = {}
#         for _prop in json_obj:
#             setattr(self, _prop, json_obj[_prop])
#         setattr(self, "class_name", class_name)
#         # The below accounts for cases where we may be using more than one
#         # repository or triplestore

#         # The 'kds_triplestoreConfigName' is the variable name in the
#         # config file that specifies the URL of the triplestore
#         if not hasattr(self, "kds_triplestoreConfigName"):
#             self.kds_triplestoreConfigName = "TRIPLESTORE_URL"
#         if not hasattr(self, "kds_repositoryConfigName"):
#             self.kds_repositoryConfigName = "REPOSITORY_URL"
#         # The kds_saveLocation specifies where to save the data i.e.
#         # in the triplestore or the repository
#         if not hasattr(self, "kds_saveLocation"):
#             self.kds_saveLocation = kwargs.get("kds_saveLocation",
#                                                "triplestore")
#         # The kds_queryLocation specifies where to query for class data
#         if not hasattr(self, "kds_queryLocation"):
#             self.kds_queryLocation = "triplestore"
#         # set the triplestore and repository urls for the class
#         self.triplestore_url = fw_config().get(self.kds_triplestoreConfigName)
#         self.repository_url = fw_config().get(self.kds_repositoryConfigName)
#         if not hasattr(self, "kds_subjectPattern"):
#             self.kds_subjectPattern = kwargs.get("kds_subjectPattern",
#                     "!--baseUrl,/,ns,/,!--classPrefix,/,!--className,/,!--uuid")
#         if not hasattr(self, "kds_baseUrl"):
#             self.kds_baseUrl = kwargs.get("kds_baseUrl", fw_config().get(\
#                 "ORGANIZATION",{}).get("url", "NO_BASE_URL"))
#         if debug: pp.pprint(self.__dict__)
#         if debug: print("\nEND RdfClass.init ---------------------------\n")

#     def save(self, rdf_obj, validation_status=True):
#         """Method validates and saves passed data for the class

#         Args:
#             rdf_obj -- Current RDF Form class fields
#             validationS

#         valid_required_props = self._validate_required_properties(
#             rdf_obj,
#             old_form_data)
#         validDependancies = self._validate_dependant_props(
#             rdf_obj,
#             old_form_data)"""

#         if not DEBUG:
#             debug = False
#         else:
#             debug = True
#         if debug: print("START RdfClass.save ---------------------------\n")
#         if debug: print("kds_classUri: ", self.kds_classUri, "  ************")
#         if not validation_status:
#             return self.validate_form_data(rdf_obj)
#         _class_obj_props = rdf_obj.class_grouping.get(self.kds_classUri,[])
#         expanded_prop_list = []
#         nonlist_prop_list = []
#         for prop in _class_obj_props:
#             if get_attr(prop, "type") == 'FieldList':
#                 for entry in prop.entries:
#                     new_prop = copy.copy(prop)
#                     new_prop.data = entry.data
                    
#                     if debug: print("* * * * * ", prop.name,": ",entry.data)
#                     expanded_prop_list.append(new_prop)
#             else:
#                 nonlist_prop_list.append(prop)
#         list_save_multi = []
#         for prop in expanded_prop_list:
#             list_save_multi.append([prop] + nonlist_prop_list)
#         if len(list_save_multi) > 0:
#             save_results = []
#             for class_props in list_save_multi:
#                 save_data = self._process_class_data(rdf_obj, class_props=class_props)
#                 if debug: print("-------------- Save data:\n",pp.pprint(save_data))
#                 save_query = self._generate_save_query(save_data)
#                 if debug: print("save_query: \n", pp.pprint(save_query))
#                 if debug: print("END RdfClass.save ---------------------------\n")
#                 save_results.append(self._run_save_query(save_query))
#             consolidated = {}
#             object_values = []
#             for result in save_results:
#                 consolidated['status'] = result.get("status")
#                 object_values.append(result.get("lastSave",{}).get("objectValue"))
#             consolidated['lastSave'] = {"objectValue":",".join(object_values)}
#             return consolidated
#         else:
#             save_data = self._process_class_data(rdf_obj)
#             if debug: print("-------------- Save data:\n",pp.pprint(save_data))
#             save_query = self._generate_save_query(save_data)
#             if debug: print("save_query: \n", pp.pprint(save_query))
#             if debug: print("END RdfClass.save ---------------------------\n")
#             return self._run_save_query(save_query)
#         #return None

#     def new_uri(self, **kwargs):
#         ''' Generates a new uri for a new subject
        
#             kwargs:
#                 save_data - pass in the data to be saved for uri 
#                 calculations'''
                
#         if not DEBUG:
#             debug = False
#         else:
#             debug = False
#         if debug: print("START RdfClass.new_uri ---------------------------\n")
#         return_val = ''
#         if self.kds_saveLocation == "triplestore":
#             # get a uuid by saving an empty record to the repo and then
#             # delete the item.
#             if "!--uuid" in self.kds_subjectPattern:
#                 repository_result = requests.post(
#                                 self.repository_url,
#                                 data="",
#                 				headers={"Content-type": "text/turtle"})
#                 object_value = repository_result.text
#                 uid = re.sub(r'^(.*[#/])','',object_value)
#                 requests.delete(object_value)
#             else:
#                 uid = ''
#             if self.kds_storageType != "blanknode":
#                 if debug: print("new uid: ", uid)
#                 return_val = self.uri_patterner(uid, **kwargs)
#         return return_val
#         if debug: print("END RdfClass.new_uri ---------------------------\n")

#     def uri_patterner(self, uid, **kwargs):
#         if not DEBUG:
#             debug = False
#         else:
#             debug = True
#         if debug: print("START RdfClass.uri_patterner ---------------------\n")
#         pattern = kwargs.get("kds_subjectPattern", self.kds_subjectPattern)
#         pattern_args = pattern.split(",")
#         new_args = []
#         for arg in pattern_args:
#             if arg.startswith("!--"):
#                 if arg == "!--baseUrl":
#                     value = self.kds_baseUrl
#                 elif arg == "!--classPrefix":
#                     value = uri_prefix(self.kds_classUri).lower()
#                 elif arg == "!--className":
#                     value = nouri(self.kds_classUri)
#                 elif arg == "!--uuid":
#                     value = uid
#                 elif arg.startswith("!--slugify"):
#                     _prop_uri = arg[arg.find("(")+1:arg.find(")")]
#                     _prop_uri = pyuri(_prop_uri)
#                     data = kwargs.get('save_data',{}).get("data",[[]])
#                     _value_to_slug = ""
#                     for item in data:
#                         if item[0] == _prop_uri:
#                             _value_to_slug = \
#                                     item[1][1:item[1].find('"^^xsd')]
#                     if is_not_null(_value_to_slug):
#                         value = slugify(_value_to_slug)
#                 else:
#                     value = arg.replace("!--","")
#             else:
#                 value = arg
#             new_args.append(value)
#         new_uri = uri("".join(new_args))
#         if new_uri.startswith("http://"):
#             temp_uri = new_uri.replace("http://","").replace("//","/")
#             if temp_uri[:1] == "/":
#                 temp_uri = temp_uri[1:]
#             new_uri = "http://" + temp_uri
#         elif new_uri.startswith("https://"):
#             temp_uri = new_uri.replace("https://","").replace("//","/")
#             if temp_uri[:1] == "/":
#                 temp_uri = temp_uri[1:]
#             new_uri = "https://" + temp_uri
#         if debug: print("pattern: %s\nuid: %s\nnew_uri: %s" %
#                     (pattern, uid, new_uri))
#         # if the new_uri does not have a uid in it test for uniqueness
#         if not is_not_null(uid):
#             failed_test = True
#             i = 1
#             test_uri = new_uri
#             while failed_test:
#                 sparql = """
#                          SELECT * 
#                          WHERE {
#                             {%s ?p ?o} UNION {?s ?p %s}
#                          } LIMIT 1""" % (iri(test_uri), iri(test_uri))
#                 results = requests.post(self.triplestore_url,
#                                         data={"query": sparql, "format": "json"})
#                 if debug: print("new_uri_test: ", results.json())
#                 _uri_test = results.json().get('results').get( \
#                             'bindings', [])
#                 # if the length of the return is 0 the uri is unique
#                 if len(_uri_test) == 0:
#                     failed_test = False
#                 # if not add in incremented number to the end of the uri
#                 else:
#                     test_uri = "%s_%s" % (new_uri, i)
#                     i += 1
#             new_uri = test_uri
#         if debug: print("END RdfClass.uri_patterner -----------------------\n")
#         return new_uri

#     def validate_obj_data(self, rdf_obj, old_data):
#         '''This method will validate whether the supplied object data
#            meets the class requirements and returns the results'''
#         _validation_steps = {}
#         _validation_steps['validRequiredFields'] = \
#                 self._validate_required_properties(rdf_obj, old_data)
#         _validation_steps['validPrimaryKey'] = \
#                 self.validate_primary_key(rdf_obj, old_data)
#         _validation_steps['validFieldData'] = \
#                 self._validate_property_data(rdf_obj, old_data)
#         _validation_steps['validSecurity'] =  \
#                 self._validate_security(rdf_obj, old_data)
#         #print("----------------- Validation ----------------------\n", \
#                 #json.dumps(_validation_steps, indent=4))
#         _validation_errors = []
#         for step in _validation_steps:
#             if _validation_steps[step][0] != "valid":
#                 for _error in _validation_steps[step]:
#                     _validation_errors.append(_error)
#         if len(_validation_errors) > 0:
#             return {"success": False, "errors":_validation_errors}
#         else:
#             return {"success": True}

#     def validate_primary_key(self, rdf_obj, old_data):
#         '''query to see if PrimaryKey is Valid'''
#         if not DEBUG:
#             debug = False
#         else:
#             debug = True
#         if debug: print("START RdfClass.validate_primary_key --------------\n")
#         if debug: print("old_data:\n",json.dumps(old_data,indent=4))
#         if old_data is None:
#             old_data = {}
#         _prop_name_list = []
#         if hasattr(self, "kds_primaryKey"):
#             pkey = self.kds_primaryKey
#             if isinstance(pkey, dict):
#                 pkey = pkey.get("kds_keyCombo",[])
#             pkey = make_list(pkey)
#         else:
#             pkey = []
#         if debug: print(self.kds_classUri, " PrimaryKeys: ", pkey, "\n")
#         if len(pkey) < 1:
#             if debug: print("END RdfClass.validate_primary_key -NO pKey----\n")
#             return ["valid"] 
#         else:
#             _calculated_props = self._get_calculated_properties()
#             _old_class_data = self._select_class_query_data(old_data)
#             _new_class_data = {}
#             _query_args = [make_triple("?uri", "a", \
#                     iri(uri(self.kds_classUri)))]
#             _multi_key_query_args = copy.deepcopy(_query_args)
#             _key_changed = False
#             _prop_uri_list = []
#             _key_props = []
#             # get primary key data from the form data
#             for prop in rdf_obj:
#                 if prop.kds_propUri in pkey:
#                     _new_class_data[prop.kds_propUri] = prop.data
#                     _prop_name_list.append(prop.kds_formLabelName)
#                     _key_props.append(prop)

#             for key in pkey:
#                 _object_val = None
#                 #get the _data_value to test against
#                 _data_value = _new_class_data.get(key, _old_class_data.get(key))
#                 if is_not_null(_data_value):
#                     _range_obj = make_list(self.kds_properties[key].get(\
#                             "rdfs_range", [{}]))[0]
#                     _data_type = _range_obj.get('storageType')
#                     _range = _range_obj.get('rangeClass')
#                     if debug: print("_data_type: ", _data_type)
#                     if _data_type == 'literal':
#                         _object_val = "FILTER regex(str(?o), %s, 'i') " % \
#                             json.dumps(_data_value)
#                         #RdfDataType(_range).sparql(_data_value)
#                     else:
#                         _object_val = iri(uri(_data_value))
#                 else:
#                     # if data is missing from the key fields exit method and
#                     # return valid. *** The object value does not exist and
#                     #                   will be generated when another class
#                     #                   is saved
#                     if debug: print(\
#                         "END RdfClass.validate_primary_key - NO data-------\n")
#                     return ["valid"]
#                 # if the old_data is not equel to the newData re-evaluate
#                 # the primaryKey

#                 # if the old value is not equal to the new value need to test
#                 # the key
#                 # if the new value is to be calculated, i.e. a dependant class
#                 # generating a value then we don't need to test the key.
#                 # however if there is a supplied value and it is listed as a
#                 # calculated property we need to test.
#                 if debug: print("old: %s\nNew: %s\nKey: %s\nCalc_props: %s" % \
#                         (_old_class_data.get(key),
#                          _new_class_data.get(key),
#                          key,
#                          _calculated_props))    
#                 if (_old_class_data.get(key) != _new_class_data.get(key)) and \
#                         ((key not in _calculated_props) or \
#                         _new_class_data.get(key) is not None):
                    
#                     _key_changed = True
#                     if _object_val:
#                         if str(_object_val).startswith("FILTER"):
#                             arg_trip = make_triple("?uri", iri(uri(key)), "?o")
#                             _query_args.append(arg_trip)
#                             _query_args.append("FILTER (!(isIri(?o))) .")
#                             _query_args.append(_object_val) 
#                             _multi_key_query_args.append(arg_trip)
#                             _multi_key_query_args.append(\
#                                     "FILTER (!(isIri(?o))) .")
#                             _multi_key_query_args.append(_object_val) 
#                         else:    
#                             _query_args.append(make_triple("?uri", 
#                                                            iri(uri(key)), \
#                                                            _object_val))    
#                             _multi_key_query_args.append(make_triple("?uri", \
#                                     iri(uri(key)), _object_val))
#                 else:
#                     if _object_val:
#                         _multi_key_query_args.append(make_triple("?uri", \
#                                 iri(uri(key)), _object_val))
#                     else:
#                         _key_changed = False
#             # if the primary key changed in the form we need to
#             # query to see if there is a violation with the new value

#             if _key_changed:
#                 if len(pkey) > 1:
#                     args = _multi_key_query_args
#                 else:
#                     args = _query_args
#                 sparql = '''
#                          {}\nSELECT DISTINCT (COUNT(?uri)>0 AS ?keyViolation)
#                          {{\n{}\n}}\nGROUP BY ?uri'''.format(\
#                                 rdfw().get_prefix(),
#                                 "\n".join(args))
#                 if debug: print("----------- PrimaryKey query:\n", sparql)
#                 _key_test_results =\
#                         requests.post(\
#                                 self.triplestore_url,
#                                 data={"query": sparql, "format": "json"})
#                 if debug: print("_key_test_results: ", _key_test_results.json())
#                 _key_test = _key_test_results.json().get('results').get( \
#                         'bindings', [])
#                 if debug: print(_key_test)
#                 if len(_key_test) > 0:
#                     _key_test = _key_test[0].get('keyViolation', {}).get( \
#                             'value', False)
#                 else:
#                     _key_test = False


#                 if not _key_test:
#                     if debug: print(\
#                         "END RdfClass.validate_primary_key - Key Passed --\n")
#                     return ["valid"]
#                 else:
#                     error_msg = "This {} aleady exists.".format(
#                                         " / ".join(_prop_name_list))
#                     for prop in _key_props:
#                         if hasattr(prop, "errors"):
#                             if isinstance(prop.errors, list):
#                                 prop.errors.append(error_msg)
#                             else:
#                                 prop.errors = [error_msg]
#                         else:
#                             setattr(prop, "errors", [error_msg])
#                     return [{"errorType":"primaryKeyViolation",
#                              "formErrorMessage": error_msg,
#                              "errorData":{"class": self.kds_classUri,
#                                           "propUri": pkey}}]
#             if debug: print(\
#                 "START RdfClass.validate_primary_key - Skipped Everything--\n")
#             return ["valid"]

#     def list_required(self):
#         '''Returns a set of the required properties for the class'''
#         _required_list = set()
#         for _prop, _value in self.kds_properties.items():
#             if _value.get('kds_requiredByDomain') == self.kds_classUri:
#                 _required_list.add(_prop)
#         try:
#             if isinstance(self.primaryKey, list):
#                 for key in self.primaryKey:
#                     _required_list.add(key)
#             else:
#                 _required_list.add(self.primaryKey)
#         except:
#             pass
#         return _required_list

#     def list_properties(self):
#         '''Returns a set of the properties used for the class'''
#         property_list = set()
#         for p in self.kds_properties:
#             property_list.add(self.kds_properties[p].get('propUri'))
#         return property_list

#     def list_dependant(self):
#         '''Returns a set of properties that are dependent upon the
#         creation of another object'''
#         _dependent_list = set()
#         for _prop in self.kds_properties:
#             _range_list = make_list(self.kds_properties[_prop].get('rdfs_range'))
#             for _row in _range_list:
#                 if _row.get('storageType') == "object" or \
#                         _row.get('storageType') == "blanknode":
#                     _dependent_list.add(_prop)
#         _return_obj = []
#         for _dep in _dependent_list:
#             _range_list = make_list(self.kds_properties[_dep].get('rdfs_range'))
#             for _row in _range_list:
#                 if _row.get('storageType') == "object" or \
#                    _row.get('storageType') == "blanknode":
#                     _return_obj.append(
#                         {"kds_propUri": self.kds_properties[_dep].get("kds_propUri"),
#                          "kds_classUri": _row.get("rangeClass")})
#         return _return_obj

#     def get_property(self, prop_uri):
#         '''Method returns the property json object

#         keyword Args:
#             prop_name: The Name of the property
#             prop_uri: The URI of the property
#             ** the PropName or URI is required'''
#         try:
#             return self.kds_properties.get(prop_uri)
#         except:
#             return None

#     def _validate_required_properties(self, rdf_obj, old_data):
#         '''Validates whether all required properties have been supplied and
#             contain data '''
#         debug = False
#         _return_error = []
#         #create sets for evaluating requiredFields
#         _required = self.list_required()
#         if debug: print("Required Props: ", _required)
#         _data_props = set()
#         _deleted_props = set()
#         for prop in rdf_obj:
#             #remove empty data properties from consideration
#             if debug: print(prop,"\n")
#             if is_not_null(prop.data) or prop.data != 'None':
#                 _data_props.add(prop.kds_propUri)
#             else:
#                 _deleted_props.add(prop.kds_propUri)
#         # find the properties that already exist in the saved class data
#         _old_class_data = self._select_class_query_data(old_data)
#         for _prop in _old_class_data:
#             # remove empty data properties from consideration
#             if is_not_null(_old_class_data[_prop]) or _old_class_data[_prop]\
#                     != 'None':
#                 _data_props.add(_prop)
#         # remove the _deleted_props from consideration and add calculated props
#         _valid_props = (_data_props - _deleted_props).union( \
#                 self._get_calculated_properties())
#         #Test to see if all the required properties are supplied
#         missing_required_properties = _required - _valid_props
#         if len(missing_required_properties) > 0:
#             _return_error.append({
#                 "errorType":"missing_required_properties",
#                 "errorData":{
#                     "class":self.kds_classUri,
#                     "properties":make_list(missing_required_properties)}})
#         if len(_return_error) > 0:
#             _return_val = _return_error
#         else:
#             _return_val = ["valid"]
#         return _return_val

#     def _get_calculated_properties(self):
#         '''lists the properties that will be calculated if no value is
#            supplied'''
#         _calc_list = set()
#         # get the list of processors that will calculate a value for a property
#         _value_processors = rdfw().value_processors
#         for _prop in self.kds_properties:
#             # Any properties that have a default value will be generated at
#             # time of save
#             if is_not_null(self.kds_properties[_prop].get('kds_defaultVal')):
#                 _calc_list.add(self.kds_properties[_prop].get('kds_propUri'))
#             # get the processors that will run on the property
#             _processors = make_list(self.kds_properties[_prop].get(\
#                     'kds_propertyProcessing', []))
#             # find the processors that will generate a value
#             for _processor in _processors:
#                 #print("processor: ", processor)
#                 if _processor.get("rdf_type") in _value_processors:
#                     _calc_list.add(_prop)
#         #any dependant properties will be generated at time of save
#         _dependent_list = self.list_dependant()
#         # properties that are dependant on another class will assume to be
#         # calculated
#         for _prop in _dependent_list:
#             _calc_list.add(_prop.get("kds_propUri"))
#         return remove_null(_calc_list)

#     def _validate_dependant_props(self, rdf_obj, old_data):
#         '''Validates that all supplied dependant properties have a uri as an
#             object'''
#         # dep = self.list_dependant()
#         # _return_error = []
#         _data_props = set()
#         for _prop in rdf_obj:
#             #remove empty data properties from consideration
#             if is_not_null(_prop.data):
#                 _data_props.add(_prop.kds_propUri)
#         '''for p in dep:
#             _data_value = data.get(p)
#             if (is_not_null(_data_value)):
#                 propDetails = self.kds_properties[p]
#                 r = propDetails.get('range')
#                 literalOk = false
#                 for i in r:
#                     if i.get('storageType')=='literal':
#                         literalOk = True
#                 if not is_valid_object(_data_value) and not literalOk:
#                     _return_error.append({
#                         "errorType":"missingDependantObject",
#                         "errorData":{
#                             "class":self.kds_classUri,
#                             "properties":propDetails.get('propUri')}})
#         if len(_return_error) > 0:
#             return _return_error
#         else:'''
#         return ["valid"]

#     def _validate_property_data(self, rdf_obj, old_data):
#         return ["valid"]

#     def _validate_security(self, rdf_obj, old_data):
#         return ["valid"]

#     def _process_class_data(self, rdf_obj, **kwargs):
#         '''Reads through the processors in the defination and processes the
#             data for saving'''
#         if not DEBUG:
#             debug = False
#         else:
#             debug = True
#         if debug: print("START rdfclass.RdfClass._process_class_data ------\n")
#         _pre_save_data = {}
#         _save_data = {}
#         _processed_data = {}
#         obj = {}
#         _required_props = self.list_required()
        
#         _calculated_props = self._get_calculated_properties()
#         _old_data = self._select_class_query_data(rdf_obj.query_data)
#         # cycle through the form class data and add old, new, doNotSave and
#         # processors for each property
#         if kwargs.get("class_props"):
#             _class_obj_props = kwargs.get("class_props")
#         else:
#             _class_obj_props = rdf_obj.class_grouping.get(self.kds_classUri,[])
#         subject_uri = "<>"
#         for prop in _class_obj_props:
#             if hasattr(prop, "subject_uri"):
#                 if prop.subject_uri is not None:
#                     subject_uri = prop.subject_uri
#                     break
#         subject_uri = _old_data.get("!!!!subjectUri", "<>")
#         for prop in _class_obj_props:
#             '''if debug: print("prop dict ----------------------\n",
#                             pp.pprint(prop.__dict__),
#                             "\n---------------------\n")'''
#             _prop_uri = prop.kds_propUri
#             if debug:
#                 if _prop_uri == "schema_image":
#                     x=1
#             # gather all of the processors for the property
#             _class_prop = self.kds_properties.get(_prop_uri,{})
#             _class_prop_processors = make_list(_class_prop.get("kds_propertyProcessing"))
#             _form_prop_processors = make_list(prop.kds_processors)
#             # clean the list of processors by sending a list based on
#             # precedence i.e. the form processors should override the rdf_class
#             # processors
#             processors = clean_processors([_form_prop_processors,
#                                            _class_prop_processors],
#                                            self.kds_classUri)
#             # remove the property from the list of required properties
#             # required properties not in the form will need to be addressed
#             _required_prop = False
#             if _prop_uri in _required_props:
#                 _required_props.remove(_prop_uri)
#                 _required_prop = True
#             # remove the property from the list of calculated properties
#             # calculated properties not in the form will need to be addressed
#             if _prop_uri in _calculated_props:
#                 _calculated_props.remove(_prop_uri)
#             # add the information to the _pre_save_data object
#             if not _pre_save_data.get(_prop_uri):
#                 _pre_save_data[_prop_uri] =\
#                         {"new":prop.data,
#                          "old":prop.old_data,
#                          "classUri": prop.kds_classUri,
#                          "required": _required_prop,
#                          "editable": prop.editable,
#                          "doNotSave": prop.doNotSave,
#                          "processors": processors}
#             else:
#                 _temp_list = make_list(_pre_save_data[_prop_uri])
#                 _temp_list.append(\
#                         {"new":prop.data,
#                          "old":prop.old_data,
#                          "classUri": prop.kds_classUri,
#                          "required": _required_prop,
#                          "editable": prop.editable,
#                          "doNotSave": prop.doNotSave,
#                          "processors": processors})
#                 _pre_save_data[_prop_uri] = _temp_list
#         # now deal with missing required properties. cycle through the
#         # remaing properties and add them to the _pre_save_data object
#         for _prop_uri in _required_props:
#             _class_prop = self.kds_properties.get(_prop_uri,{})
#             _class_prop_processors = clean_processors([make_list(\
#                             _class_prop.get("kds_propertyProcessing"))],
#                             self.kds_classUri)
#             if _prop_uri == "schema_alternativeName":
#                 x=1
#             # remove the prop from the remaining calculated props
#             if _prop_uri in _calculated_props:
#                 _calculated_props.remove(_prop_uri)
#             if not _pre_save_data.get(_prop_uri):
#                 _pre_save_data[_prop_uri] =\
#                         {"new":NotInFormClass(),
#                          "old":_old_data.get(_prop_uri),
#                          "doNotSave":False,
#                          "classUri": self.kds_classUri,
#                          "required": True,
#                          "editable": True,
#                          "processors":_class_prop_processors,
#                          "defaultVal":_class_prop.get("kds_defaultVal")}
#                 if debug: print("psave: ", _pre_save_data[_prop_uri])
#             else:
#                 _temp_list = make_list(_pre_save_data[_prop_uri])
#                 _pre_save_data[_prop_uri] = _temp_list.append(\
#                         {"new":NotInFormClass(),
#                          "old":_old_data.get(_prop_uri),
#                          "doNotSave": False,
#                          "classUri": self.kds_classUri,
#                          "editable": True,
#                          "processors":_class_prop_processors,
#                          "defaultVal":_class_prop.get("kds_defaultVal")})

#         # now deal with missing calculated properties. cycle through the
#         # remaing properties and add them to the _pre_save_data object
#         if debug: print("calc props: ", _calculated_props)
#         for _prop_uri in _calculated_props:
#             if debug: print("########### _calculated_props: ")
#             _class_prop = self.kds_properties.get(_prop_uri,{})
#             _class_prop_processors = clean_processors([make_list(\
#                     _class_prop.get("kds_propertyProcessing"))],
#                     self.kds_classUri)
#             if not _pre_save_data.get(_prop_uri):
#                 _pre_save_data[_prop_uri] =\
#                         {"new":NotInFormClass(),
#                          "old":_old_data.get(_prop_uri),
#                          "doNotSave":False,
#                          "processors":_class_prop_processors,
#                          "defaultVal":_class_prop.get("kds_defaultVal")}
#             else:
#                 _temp_list = make_list(_pre_save_data[_prop_uri])
#                 _pre_save_data[_prop_uri] =\
#                         _temp_list.append(\
#                                 {"new":NotInFormClass(),
#                                  "old":_old_data.get(_prop_uri),
#                                  "doNotSave":False,
#                                  "processors":_class_prop_processors,
#                                  "defaultVal":_class_prop.get("kds_defaultVal")})
#         # cycle through the consolidated list of _pre_save_data to
#         # test the security, run the processors and calculate any values
#         for _prop_uri, prop in _pre_save_data.items():
#             # ******* doNotSave property is set during form field creation
#             # in get_wtform_field method. It tags fields that are there for
#             # validation purposes i.e. password confirm fields ******

#             if isinstance(prop, list):
#                 # a list with in the property occurs when there are
#                 # multiple fields tied to the property. i.e.
#                 # password creation or change / imagefield that
#                 # takes a URL or file
#                 for _prop_instance in prop:
#                     if _prop_instance.get("doNotSave", False):
#                         _pre_save_data[_prop_uri].remove(_prop_instance)
#                 if len(make_list(_pre_save_data[_prop_uri])) == 1:
#                     _pre_save_data[_prop_uri] = _pre_save_data[_prop_uri][0]
#             # doNotSave = prop.get("doNotSave", False)
#         for _prop_uri, _prop in _pre_save_data.items():
#             # send each property to be proccessed
#             if _prop:
#                 obj = self._process_prop({"propUri":_prop_uri,
#                                           "prop": _prop,
#                                           "processedData": _processed_data,
#                                           "preSaveData": _pre_save_data})
#                 _processed_data = obj["processedData"]
#                 _pre_save_data = obj["preSaveData"]
#         if debug: print("PreSaveData----------------")
#         if debug: print(json.dumps(dumpable_obj(_pre_save_data), indent=4))
#         _save_data = {"data":self.__format_data_for_save(_processed_data,
#                                                          _pre_save_data),
#                       "subjectUri":subject_uri}
#         return _save_data

#     def _generate_save_query(self, save_data_obj, subject_uri=None):
#         if not DEBUG:
#             debug = False
#         else:
#             debug = True
#         if debug: print("START RdfClass._generate_save_query -------------\n")
#         _save_data = save_data_obj.get("data")
#         # find the subject_uri positional argument or look in the save_data_obj
#         # or return <> as a new node
#         if not subject_uri:
#             subject_uri = iri(uri(save_data_obj.get('subjectUri', "<>")))
#         _save_type = self.kds_storageType
#         if subject_uri == "<>" and _save_type.lower() == "blanknode":
#             _save_type = "blanknode"
#         else:
#             _save_type = "object"
#         new_status = False
#         if self.kds_saveLocation == "triplestore" and subject_uri == "<>":
#             subject_uri = iri(self.new_uri(save_data=save_data_obj))
#             new_status = True
#         _bn_insert_clause = []
#         _insert_clause = ""
#         _delete_clause = ""
#         _where_clause = ""
#         _prop_set = set()
#         i = 1
#         j = 1000
#         if debug: print("save data in generateSaveQuery\n", \
#                     pp.pprint(_save_data))
#         # test to see if there is data to save
#         if len(_save_data) > 0:
#             for prop in _save_data:
#                 # test to see if the object value is a blank node
#                 if isinstance(prop[1], str) and prop[1][:1] == "[":
#                     # build the blanknode linkage
#                     prop_range_list = get_attr(self, pyuri(_prop_uri))['rdfs_range']
#                     for rng in make_list(prop_range_list):
#                         if rng.get("storageType") == "blanknode":
#                             prop_range = rng.get("rangeClass")
#                     linked_prop = uri(get_attr(rdfw(),prop_range).kds_blankNodeLink)
#                     line1 = make_triple(subject_uri, _prop_uri, "?" + str(j))
#                     line2 = make_triple("?" + str(j), iri(uri(linked_prop)))
#                     #_bn_delete_clause.append(
#                 _prop_set.add(uri(prop[0]))
#                 _prop_iri = iri(uri(prop[0]))
#                 if not isinstance(prop[1], DeleteProperty):
#                     _obj_val = uri(prop[1])
#                     _insert_clause += "{}\n".format(\
#                                         make_triple(subject_uri, _prop_iri, _obj_val))
#                     _bn_insert_clause.append("\t{} {}".format(_prop_iri, _obj_val))
#             if subject_uri != '<>' and not new_status:
#                 for prop in _prop_set:
#                     _prop_iri = iri(uri(prop))
#                     _delete_clause += "{}\n".format(\
#                                     make_triple(subject_uri, _prop_iri, "?"+str(i)))
#                     _where_clause += "OPTIONAL {{ {} }} .\n".format(\
#                                     make_triple(subject_uri, _prop_iri, "?"+str(i)))
#                     i += 1
#             else:
#                 _obj_val = iri(uri(self.kds_classUri))
#                 _insert_clause += make_triple(subject_uri, "a", _obj_val) + \
#                         "\n"
#                 _bn_insert_clause.append("\t a {}".format(_obj_val))
#             if _save_type == "blanknode":
#                 _save_query = "[\n{}\n]".format(";\n".join(_bn_insert_clause))
#             else:
#                 if subject_uri != '<>' and not new_status:
#                     save_query_template = Template("""{{ prefix }}
#                                     DELETE \n{
#                                     {{ _delete_clause }} }
#                                     INSERT \n{
#                                     {{ _insert_clause }} }
#                                     WHERE \n{
#                                     {{ _where_clause }} }""")
#                     _save_query = save_query_template.render(
#                         prefix=rdfw().get_prefix(),
#                         _delete_clause=_delete_clause,
#                         _insert_clause=_insert_clause,
#                         _where_clause=_where_clause)
#                 else:
#                     _save_query = "{}\n\n{}".format(
#                         rdfw().get_prefix("turtle"),
#                         _insert_clause)
#             if debug: print(_save_query)
#             if debug: print("END RdfClass._generate_save_query -------------\n")
#             return {"query":_save_query, "subjectUri":subject_uri,
#                     "new_status":new_status}
#         else:
#             if debug: print("END RdfClass._generate_save_query -------------\n")
#             return {"subjectUri":subject_uri}

#     def _run_save_query(self, save_query_obj, subject_uri=None):
#         if not DEBUG:
#             debug = False
#         else:
#             debug = False
#         _save_query = save_query_obj.get("query")
#         if debug: print("START RdfClass._run_save_query -------------------\n")
#         if debug: print("triplestore: ", self.triplestore_url)
#         if debug: print("repository: ", self.repository_url)
#         if not subject_uri:
#             subject_uri = save_query_obj.get("subjectUri")
#         if debug: print("_save_query:\n", _save_query)
#         if _save_query:
#             # a "[" at the start of the save query denotes a blanknode
#             # return the blanknode as the query result
#             if _save_query[:1] == "[":
#                 object_value = _save_query
#             else:
#                 # if there is no subject_uri create a new entry in the
#                 # repository
#                 if subject_uri == "<>" or save_query_obj.get("new_status"):
#                     if debug: print("Enter New")
#                     if self.kds_saveLocation == "repository":
#                         repository_result = requests.post(
#                                 self.repository_url,
#                                 data=_save_query,
#                                 headers={"Content-type": "text/turtle"})
#                         if debug: print("repository_result: ",
#             	                        repository_result,
#             	                        " ",
#             	                        repository_result.text)
#                         object_value = repository_result.text
#                     elif self.kds_saveLocation == "triplestore":
#                         triplestore_result = requests.post(
#                                 url=self.triplestore_url,
#                                 headers={"Content-Type":
#                                          "text/turtle"},
#                                 data=_save_query)
#                         if debug: print("triplestore_result: ",
#                                         triplestore_result,
#                                         " ",
#                                         triplestore_result.text)
#                         object_value = subject_uri
#                     elif self.kds_saveLocation == "elasticsearch":
#                             print ("**************** ES Connection NOT Built")
#                     elif self.kds_saveLocation == "sql_database":
#                             print ("**************** SQL Connection NOT Built")
#                 # if the subject uri exists send an update query to the
#                 # specified datastore
#                 else:
#                     if debug: print("Enter Update")
#                     if self.kds_saveLocation == "repository":
#                         _headers = {"Content-type":
#                                     "application/sparql-update"}
#                         _url = clean_iri(subject_uri)
#                         repository_result = \
#                                 requests.patch(_url, data=_save_query,
#             				                   headers=_headers)
#                         if debug: print("repository_result: ",
#             	                        repository_result,
#             	                        " ",
#             	                        repository_result.text)
#                         object_value = iri(subject_uri)
#                     elif self.kds_saveLocation == "triplestore":
#                         _url = self.triplestore_url
#                         triplestore_result = requests.post(_url,
#                                 data={"update":_save_query})
#                         if debug: print("triplestore_result: ",
#                                         triplestore_result,
#                                         " ",
#                                         triplestore_result.text)
#                         object_value = iri(subject_uri)
#                     elif self.kds_saveLocation == "elasticsearch":
#                         print ("**************** ES Connection NOT Built")
#                     elif self.kds_saveLocation == "sql_database":
#                         print ("**************** SQL Connection NOT Built")
#             if debug: print("END RdfClass._run_save_query ----------------\n")
#             return {"status": "success",
#                     "lastSave": {
#                         "objectValue": object_value}
#                    }
#         else:
#             if debug: print("Enter No Data to Save")
#             if debug: print("END RdfClass._run_save_query ---NO DATA-------\n")
#             return {"status": "success",
#                     "lastSave": {
#                         "objectValue": iri(subject_uri),
#                         "comment": "No data to Save"}
#                    }

#     def _process_prop(self, obj):
#         # obj = propUri, prop, processedData, _pre_save_data
#         # !!!!!!! the merge_prop function will need to be relooked for
#         # instances where we have multiple property entries i.e. a fieldList
#         if not DEBUG:
#             debug = False
#         else:
#             debug = False
#         if debug: print("START RdfClass._process_prop -------------------\n")
#         if len(make_list(obj['prop'])) > 1:
#             obj = self.__merge_prop(obj)
#         processors = obj['prop'].get("processors", [])
#         _prop_uri = obj['propUri']
#         # process properties that are not in the form
#         if isinstance(obj['prop'].get("new"), NotInFormClass) and \
#                 not is_not_null(obj['prop'].get("old")):
#             # process required properties
#             if obj['prop'].get("required"):
#                 # run all processors: the processor determines how to
#                 # handle if there is old data
#                 if len(processors) > 0:
#                     for processor in processors.values():
#                         obj = run_processor(processor, obj)
#                 # if the processors did not calculate a value for the
#                 # property attempt to calculte from the default
#                 # property settings
#                 if not obj['prop'].get('calcValue', False):
#                     obj_value = calculate_default_value(obj['prop'])
#                     obj['processedData'][obj['propUri']] = obj_value
#             #else:
#                 # need to decide if you want to calculate properties
#                 # that are not required and not in the form
#         # if the property is editable process the data
#         elif obj['prop'].get("editable"):
#             # if the old and new data are different
#             if clean_iri(obj['prop'].get("new")) != \
#                                     clean_iri(obj['prop'].get("old")):
#                 # if the new data is null and the property is not
#                 # required run the processors first then mark property for
#                 # deletion if it is still should be deleted
#                 if not is_not_null(obj['prop'].get("new")) and not \
#                                                 obj['prop'].get("required"):
#                     for processor in processors.values():
#                             obj = run_processor(processor, obj)
#                     if not obj['prop']['doNotSave']:
#                         obj['processedData'][_prop_uri] = DeleteProperty()
#                 # if the property has new data
#                 elif is_not_null(obj['prop'].get("new")):
#                     if len(processors) > 0:
#                         for processor in processors.values():
#                             obj = run_processor(processor, obj)
#                         if not obj['prop'].get('calcValue', False):
#                             obj['processedData'][_prop_uri] = \
#                                                        obj['prop'].get("new")
#                     else:
#                         obj['processedData'][_prop_uri] = obj['prop'].get("new")
#         if debug: print("END RdfClass._process_prop -------------------\n")
#         return obj

#     def __calculate_property(self, obj):
#         ''' Reads the obj and calculates a value for the property'''
#         return obj

#     def __merge_prop(self, obj):
#         '''This will need to be expanded to handle more cases right now
#         the only case is an image '''
#         #_prop_list = obj['prop']
#         _keep_image = -1

#         for i, prop in enumerate(obj['prop']):
#             if isinstance(prop['new'], FileStorage):
#                 if prop['new'].filename:
#                     _keep_image = i
#                     break
#         for i, prop in enumerate(obj['prop']):
#             if i != _keep_image:
#                 obj['prop'].remove(prop)
#         obj['prop'] = obj['prop'][0]
#         return obj
#         '''_prop_list = obj['prop']
#         _class_prop = self.get_property(prop_uri=obj['propUri'])
#         propRange = _class_prop.get('''
#         '''for prop in _prop_list:
#             for name, attribute in prop.items():
#                 if conflictingValues.get(name):
#                     if isinstance(conflictingValues.get(name), list):
#                         if not attribute in conflictingValues.get(name):
#                             conflictingValues[name].append(attribute)
#                     elif conflictingValues.get(name) != attribute:
#                         conflictingValues[name] = [conflictingValues[name],
#                                                    attribute]
#                 else:
#                     conflictingValues[name] = attribute'''

#     def __format_data_for_save(self, processed_data, pre_save_data):
#         ''' takes the processed data and formats the values for the sparql
#             query '''
#         if not DEBUG:
#             debug = False
#         else:
#             debug = True
#         if debug: print("START RdfClass.__format_data_for_save -----------\n")
#         _save_data = []
#         #if "obi_recipient" in pre_save_data.keys():
#         #    x=y
#         if debug: print("format data***********\n")
#         if debug: pp.pprint(processed_data)
#         if not processed_data:
#             processed_data = {}
#         # cycle throught the properties in the processed data
#         for _prop_uri, prop in processed_data.items():
#             # if the property is maked for deletion add it to the save list
#             if isinstance(prop, NotInFormClass):
#                 pass
#             elif isinstance(prop, DeleteProperty):
#                 _save_data.append([_prop_uri, prop])
#             # if the property is a file object send it to the repository and
#             # add the new uri to the save data list
#             elif isinstance(prop, FileStorage):
#                 _file_iri = save_file_to_repository(\
#                         prop, pre_save_data[_prop_uri][0].get('old'))
#                 _save_data.append([_prop_uri, _file_iri])
#             # otherwise determine the range of the property and format it in
#             # the correct sparl format
#             else:
#                 # some properties have more than one option for the object
#                 # value i.e. schema:image can either store a ImageObject or
#                 # a Url to an image. We need to determine the range options
#                 _range_list = make_list(self.kds_properties[_prop_uri].get(\
#                         "rdfs_range", [{}]))
#                 _storage_types = set()
#                 _data_types = set()
#                 # cycle through the range_list and get the sets of options
#                 for _range_dict in _range_list:
#                     _storage_types.add(_range_dict.get('storageType'))
#                     if _range_dict.get('storageType') == "literal":
#                         _data_types.add(_range_dict.get('rangeClass'))
#                 _data_type = "xsd_string"
#                 for _type in _data_types:
#                     if "xsd" in _type:
#                         _data_type = _type
#                 # cycle through the items in the current prop
#                 _value_list = make_list(prop)
#                 for item in _value_list:
#                     if 'object' in _storage_types or 'blanknode' in \
#                             _storage_types:
#                         uri_test = uri(item)
#                         if debug: print(_prop_uri, " - ", uri_test)
#                         if uri_test.startswith("http"):
#                             _save_data.append([_prop_uri, iri(uri(item))])
#                         elif 'literal' in _storage_types:
#                             _save_data.append([_prop_uri, RdfDataType(\
#                                     _data_type).sparql(str(item))])
#                         else:
#                             _save_data.append([_prop_uri, iri(uri(item))])
#                     else:
#                         _item = str(item).encode('unicode_escape')
#                         _save_data.append([_prop_uri, RdfDataType(\
#                                 _data_type).sparql(str(item))])
#         if debug: print("END RdfClass.__format_data_for_save -----------\n")
#         return _save_data

#     def _select_class_query_data(self, old_data):
#         ''' Find the data in query data that pertains to this class instance
#             returns dictionary of data with the subject_uri stored as
#             !!!!subject'''

#         #print("__________ class queryData:\n", \
#         #                        json.dumps(dumpable_obj(old_data), indent=4))
#         _old_class_data = {}
#         if old_data:
#             # find the current class data from the query
#             if isinstance(old_data, list):
#                 for entry in old_data:
#                     for _subject_uri, value in entry.items():
#                         _class_types = make_list(value.get("rdf_type", []))
#                         for _rdf_type in _class_types:
#                             if _rdf_type == self.kds_classUri or \
#                                     _rdf_type == "<%s>" % self.kds_classUri:
#                                 _old_class_data = value
#                                 _old_class_data["!!!!subjectUri"] = _subject_uri
#                                 break
#             else:
#                 for _subject_uri in old_data:
#                     _class_types = make_list(old_data[_subject_uri].get( \
#                         "rdf_type", []))
#                     for _rdf_type in _class_types:
#                         if _rdf_type == self.kds_classUri or \
#                                     _rdf_type == "<%s>" % self.kds_classUri:
#                             _old_class_data = old_data[_subject_uri]
#                             _old_class_data["!!!!subjectUri"] = _subject_uri
#                         break

#         return _old_class_data
