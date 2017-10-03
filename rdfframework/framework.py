"""Base Module for RDFFRamework Project"""

__author__ = "Mike Stabile, Jeremy Nelson"


import os
import sys
import inspect
import logging
import time
import operator
import requests
import pdb
import rdflib

from flask import json

from rdfframework.utilities import iri, is_not_null, make_list, \
        remove_null, clean_iri, convert_spo_to_dict, convert_ispo_to_dict, \
        render_without_request, create_namespace_obj, \
        convert_obj_to_rdf_namespace, pyuri, nouri, pp, iris_to_strings, \
        convert_obj_to_rdf_namespace, convert_spo_def, \
        make_class, RdfConfigManager, RdfNsManager

from rdfframework.sparql import get_data, get_linker_def_item_data, \
        get_class_def_item_data, run_sparql_query, create_tstore_namespace


MODULE_NAME = os.path.basename(inspect.stack()[0][1])
CFG = RdfConfigManager()
NSM = RdfNsManager()

class RdfFrameworkSingleton(type):
    """Singleton class for the RdfFramewodk that will allow for only one
    instance of the RdfFramework to be created."""

    _instances = {}
    def __call__(cls, *args, **kwargs):
        if not CFG.is_initialized:
            print("The RdfConfigManager has not been initialized!")
        if cls not in cls._instances:
            cls._instances[cls] = super(RdfFrameworkSingleton, 
                    cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class RdfFramework(metaclass=RdfFrameworkSingleton):
    ''' base class for Knowledge Links' Graph database RDF vocabulary
        framework'''

    rdf_class_dict = {}       # stores the Triplestore defined class defintions
    class_initialized = False # used to state if the the class was properly
                              #     initialized with RDF definitions
    rdf_form_dict = {}        # stores the Triplestore defined form definitions
    forms_initialized = False # used to state if the form definitions have
                              #     been initialized
    rdf_app_dict = {}         # stors the the Triplestore definged application
                              #     settings
    app_initialized = False   # states if the application has been initialized
    value_processors = []
    apis_initialized = False
    linkers_initialized = False

    ln = "%s.RdfFramework" % MODULE_NAME
    # set specific logging handler for the module allows turning on and off
    # debug as required
    log_level = logging.DEBUG
    
    def __init__(self, **kwargs):
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        self.root_file_path = CFG.ROOT_FILE_PATH
        self._set_rdf_def_filelist()
        self.form_list = {}
        # if the the definition files have been modified since the last json
        # files were saved reload the definition files
        if kwargs.get('reset',False) or self.last_def_mod > self.last_json_mod:
            reset = True
        else:
            reset = False
        if not os.path.isdir(CFG.JSON_LOCATION):
            print("JSON cache directory not found.\nCreating directory")
            reset = True
            os.makedirs(CFG.JSON_LOCATION)
        if not os.path.exists(os.path.join(CFG.JSON_LOCATION,
                                           "app_query.json")):
            reset = True
        # verify that the server core is up and running
        servers_up = True
        if kwargs.get('server_check', True):
            servers_up = verify_server_core(600, 0)
        else:
            lg.info("server check skipped")
        if not servers_up:
            lg.info("Sever core not initialized --- Framework Not loaded")
        if servers_up:
            lg.info("*** Loading Framework ***")
            self._load_rdf_data(reset)
            self._load_app(reset)
            # self._generate_classes(reset)
            # self._generate_linkers(reset)
            #self._generate_forms(reset)
            #self._generate_apis(reset)
            lg.info("*** Framework Loaded ***")

    def load_default_data(self):
        ''' reads default data in the fw_config and attempts to add it
            to the server core i.e. inital users and organizations'''

        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)     
        # test to see if the default data was already loaded
        sparql = '''
            SELECT ?default_loaded
            WHERE {
                ?uri kds:defaultLoaded ?default_loaded .
            }'''
        result = requests.post(CFG.TRIPLESTORE.url,
                               data={"query": self.get_prefix() + sparql,
                                     "format": "json"})
        value = result.json().get('results', {}).get('bindings', [])
        if len(value) == 0:
            # if not loaded save the data
            data_list = make_list(CFG.FRAMEWORK_DEFAULT)
            for data in data_list:
                form_class = rdf_framework_form_factory(data['form_path'])
                form_data = data['form_data']
                form = form_class()
                #pp.pprint(form.__dict__)
                for prop in form.rdf_field_list:
                    if prop.type != "FieldList":
                        #print(prop.name, " - ", form_data.get(prop.name))
                        #pp.pprint(prop.__dict__)
                        prop.data = form_data.get(prop.name)
                form.save()
            # tag the triplestore that the data has been loaded
            save_data = ' kdr:appData kds:defaultLoaded "true"^^xsd:string .'
            save_query = self.get_prefix("turtle") + save_data
            #responce = requests.post(fw_config().get("REPOSITORY_URL"),
            #               data=save_query,
            #               headers={"Content-type": "text/turtle"})
            triplestore_result = requests.post(
                                url=CFG.TRIPLESTORE.url,
                                headers={"Content-Type":
                                         "text/turtle"},
                                data=save_query)

    def form_exists(self, form_path):
        '''Tests to see if the form and instance is valid'''
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        if form_path in self.form_list.keys():
            return self.form_list[form_path]
        else:
            return False

    def api_exists(self, api_path):
        '''Tests to see if the form and instance is valid'''
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        if api_path in self.api_list.keys():
            return self.api_list[api_path]
        else:
            return False

    def get_form_path(self, form_uri, instance):
        ''' reads through the list of defined APIs and returns the path '''
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        for form_path, val in self.form_list.items():
            if val['form_uri'] == form_uri and val['instance_uri'] == instance:
                return form_path

    def get_api_path(self, api_uri, instance):
        ''' reads through the list of defined forms and returns the path '''
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        for api_path, val in self.api_list.items():
            if val['api_uri'] == api_uri and val['instance_uri'] == instance:
                return api_path

    def get_form_name(self, form_uri):
        '''returns the form name for a form '''
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        if form_uri:
            return pyuri(form_uri)
        else:
            return None

    def get_api_name(self, api_uri):
        '''returns the API name for an API '''
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        if api_uri:
            return pyuri(api_uri)
        else:
            return None

    def _make_form_list(self):
        ''' creates an indexed dictionary of available forms and attaches
            it to the Framework as form_list attribute'''
        _form_list = {}
        _link_list = {}
        for _form, _details in self.rdf_form_dict.items():
            _form_instr = _details.get('kds_formInstructions',{})
            _form_url = _form_instr.get(\
                    "kds_formUrl",nouri(_form))
            _instance_list = _form_instr.get(\
                    'kds_formInstance',{})
            for _instance in make_list(_instance_list):
                _instance_url = _instance.get(\
                                "kds_instanceUrl",
                                nouri(_instance.get('kds_formInstanceType','')))
                if _instance_url == "none":
                    _key = _form_url
                else:
                    _key = "{}/{}".format(_form_url, _instance_url)
                _form_title = _instance.get('kds_formTitle',
                        _form_instr.get("kds_formTitle",nouri(_form)))
                _instance_name = nouri(_instance.get('kds_formInstanceType'))
                _name_list = [_form_title]
                if _instance_name:
                    _name_list.append(_instance_name)
                _form_list[_key] = {\
                        'form_uri':_form,
                        'instance_uri':_instance.get('kds_formInstanceType',''),
                        'form_title':"-".join(_name_list)}
                _link_list["-".join(_name_list)] = _key
        self.link_list = sorted(_link_list.items(), key=operator.itemgetter(0))
        #print(self.link_list)
        self.form_list = _form_list

    def _make_api_list(self):
        ''' creates an indexed dictionary of available APIs and attaches
            it to the Framework as api_list attribute'''
        _api_list = {}
        for _api, _details in self.rdf_api_dict.items():
            _api_url = _details.get('kds_apiInstructions',{}).get(\
                    "kds_apiUrl",nouri(_api))
            _extension = _details.get('kds_apiInstructions',{}).get(\
                    'kds_apiUrlExtension')
            if not _extension:
                _key = _api_url
            else:
                _key = "{}|{}".format(_api_url, _extension)
            _api_list[_key] = {\
                    'api_uri':_api,
                    'extension':_extension}
        self.api_list = _api_list

    def _load_app(self, reset):
        ''' queries the rdf definitions and sets the framework attributes
            for the application defaults '''
        if self.app_initialized != True:
            _app_json = self._load_application_defaults(reset)
            print(1)
            self.ns_obj = create_namespace_obj(obj=_app_json)
            print(2)
            filepaths = []
            for key, flist in self.def_files.items():
                for file in flist:
                    filepaths.append(os.path.join(key, file))
            print(3)
            self.ns_obj = create_namespace_obj(filepaths=filepaths)
            print(4)
            if CFG.DEFAULT_RDF_NS:
                self.ns_obj.dict_load(CFG.DEFAULT_RDF_NS)
            print(5)
            self.rdf_app_dict = convert_obj_to_rdf_namespace(_app_json,
                                                             self.ns_obj)
            print(6)
            print("\t\t%s objects" % len(self.rdf_app_dict))
            # add the security attribute
            # add the app attribute
            _key_string = "kds_applicationSecurity"
            for _app_section in self.rdf_app_dict.values():
                try:
                    for _section_key in _app_section.keys():
                        if _section_key == _key_string:
                            self.app_security = _app_section[_section_key]
                            self.app = make_class(_app_section)
                            break
                except AttributeError:
                    pass
            # add attribute for a list of property processors that
            # will generate a property value when run
            _value_processors = []
            for _processor, value in \
                    self.rdf_app_dict.get("kds_PropertyProcessor", {}).items():
                if value.get("kds_resultType") == "propertyValue":
                    _value_processors.append(_processor)
            self.value_processors = _value_processors
            self.app_initialized = True


    def _load_application_defaults(self, reset):
        ''' Queries the triplestore for settings defined for the application in
            the kl_app.ttl file'''

        print("\tLoading application defaults")
        if reset:
            sparql = render_without_request("jsonApplicationDefaults.rq",
                                            None,
                                            graph=iri(self.def_graph))
            data = run_sparql_query(sparql, namespace=self.def_ns)
            _string_defs = data[0]['app']['value']
            print("end query")
            with open(
                os.path.join(CFG.JSON_LOCATION, "app_query.json"),
                "w") as file_obj:
                file_obj.write( _string_defs )
            print("end write")
            _json_defs = json.loads(_string_defs)
            print("end load")
        else:
            with open(
                os.path.join(CFG.JSON_LOCATION, "app_query.json")) as file_obj:
                _json_defs = json.loads(file_obj.read())
        return _json_defs

    def _load_rdf_class_defintions(self, reset):
        ''' Queries the triplestore for list of classes used in the app as
            defined in the rdfw-definitions folders'''
        print("\tLoading rdf class definitions")
        if reset:
            # get a list of all of the rdf classes being defined
            prefix = self.ns_obj.prefix()
            graph = CFG.RDF_DEFINITION_GRAPH
            sparql = render_without_request("sparqlClassDefinitionList.rq",
                                             graph=graph,
                                             prefix=prefix)
            class_qry = requests.post(CFG.TRIPLESTORE.url,
                                      data={"query": sparql, "format": "json"})
            class_list = class_qry.json().get('results').get('bindings')
            class_dict = {}
            # cycle through the classes and query for the class definitions
            for app_class in class_list:
                class_uri = iri(app_class['kdsClass']['value'])
                data = get_class_def_item_data(class_uri)
                #pdb.set_trace()
                class_dict[class_uri] = convert_ispo_to_dict(data, 
                        base=class_uri)
            class_dict = convert_obj_to_rdf_namespace(class_dict)
            with open(
                os.path.join(CFG.JSON_LOCATION,"class_query.json"),
                "w") as file_obj:
                file_obj.write( json.dumps(class_dict, indent=4) )
        else:
            with open(
                os.path.join(CFG.JSON_LOCATION, "class_query.json")) as file_obj:
                class_dict = json.loads(file_obj.read())
        return class_dict

    def _load_rdf_linker_defintions(self, reset):
        ''' Queries the triplestore for list of classes used in the app as
            defined in the rdfw-definitions folders'''
        print("\tLoading rdf linker definitions")
        if reset:
            # query the database for the linker defintions
            sparql = render_without_request(\
                    "sparqlLinkerDefinitionDataTemplate.rq",
                    prefix=self.ns_obj.prefix(),
                    definition_graph=iri(self.def_graph))
            linker_data = run_sparql_query(sparql, namespace=self.def_ns)
            linker_data = convert_spo_to_dict(linker_data,
                    method=self.def_config.get('triplestore'))
            linker_dict = convert_obj_to_rdf_namespace(linker_data, 
                                                       key_only=True,
                                                       rdflib_uri=True)
            with open(
                os.path.join(CFG.JSON_LOCATION,"linker_query.json"),
                "w") as file_obj:
                file_obj.write(json.dumps(linker_dict, indent=4))
        else:
            with open(
                os.path.join(CFG.JSON_LOCATION, "linker_query.json")) as file_obj:
                linker_dict = json.loads(file_obj.read())
        return linker_dict

    def _load_rdf_form_defintions(self, reset):
        ''' Queries the triplestore for list of forms used in the app as
            defined in the kl_app.ttl file'''
        print("\tLoading form definitions")
        if reset:
            _sparql = render_without_request("jsonFormQueryTemplate.rq",
                                             graph=CFG.RDF_DEFINITION_GRAPH)
            _form_list = requests.post(CFG.TRIPLESTORE_URL,
                                       data={"query": _sparql, "format": "json"})
            _raw_json = _form_list.json().get('results').get('bindings'\
                    )[0]['appForms']['value']
            _string_defs = _raw_json.replace('hasProperty":', 'properties":')

            with open(
                os.path.join(CFG.JSON_LOCATION, "form_query.json"),
                "w") as file_obj:
                file_obj.write( _string_defs)
            _json_defs = json.loads(_string_defs)
        else:
            with open(
                os.path.join(CFG.JSON_LOCATION, "form_query.json")) as file_obj:
                _json_defs = json.loads(file_obj.read())
        return _json_defs

    def _load_rdf_api_defintions(self, reset):
        ''' Queries the triplestore for list of forms used in the app as
            defined in the kl_app.ttl file'''
        print("\tLoading api definitions")
        if reset:
            _sparql = render_without_request("jsonApiQueryTemplate.rq",
                                             graph=CFG.RDF_DEFINITION_GRAPH)
            _api_list = requests.post(CFG.TRIPLESTORE.url,
                                       data={"query": _sparql, "format": "json"})
            _raw_json = _api_list.json().get('results').get('bindings'\
                    )[0]['appApis']['value']
            _string_defs = _raw_json.replace('hasProperty":', 'properties":')
            _json_defs = json.loads(_string_defs)
            with open(
                os.path.join(CFG.JSON_LOCATION, "api_query.json"),
                "w") as file_obj:
                file_obj.write( _string_defs )
        else:
            with open(
                os.path.join(CFG.JSON_LOCATION, "api_query.json")) as file_obj:
                _json_defs = json.loads(file_obj.read())
        return _json_defs

    def _validate_obj_by_class_reqs(self, rdf_obj):
        '''This method will cycle thhrought the objects rdf classes and
           call the classes validate_form_data method and return the results'''

        _validation_results = {}
        _validation_errors = []
        for _rdf_class in rdf_obj.class_grouping:
            _current_class = getattr(self, _rdf_class)
            _validation_results = _current_class.validate_obj_data(\
                    rdf_obj.class_grouping[_rdf_class], rdf_obj.query_data)
            if not _validation_results.get("success", True):
                _validation_errors += _validation_results.get("errors", [])
        if len(_validation_errors) > 0:
            for _error in _validation_errors:
                for _prop in make_list(_error.get("errorData", {}).get(\
                        "kds_propUri", [])):
                    _obj_prop = getattr(rdf_obj, _prop.kds_propUri)
                    if hasattr(_obj_prop, "errors"):
                        _prop.errors.append(_error.get(\
                                "formErrorMessage"))
                    else:
                        setattr(_obj_prop, "errors", [_error.get(\
                                "formErrorMessage")])
            return {"success": False, "obj":rdf_obj, "errors": \
                        _validation_errors}
        else:
            return {"success": True}


    def _load_rdf_data(self, reset=False):
        ''' loads the RDF/turtle application data to the triplestore '''
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        
        self.base_url = CFG.ORGANIZATION.get('url',"")
        self.def_config = CFG.RDF_DEFINITIONS
        self.triplestore_url = CFG.TRIPLESTORE.url
        self.def_ns = CFG.RDF_DEFINITIONS.get('namespace',
                CFG.TRIPLESTORE.get("default_ns", "kb"))
        create_tstore_namespace(self.def_ns)
        create_tstore_namespace(CFG.TRIPLESTORE.default_ns)
        # Strip off trailing forward slash for TTL template
        if self.base_url.endswith("/"):
            self.base_url = self.base_url[:-1]
        # if the extensions exist in the triplestore drop the graph
        self.def_graph = clean_iri(self.def_config.get('graph',
                CFG.TRIPLESTORE.get('default_graph', "")))
        if reset:
            if self.def_config['method'] == "graph":
                sparql = "DROP GRAPH %s;" % self.def_config.graph
                graph = clean_iri(self.def_config.graph)
            elif self.def_config.method == "namespace":
                sparql = "DROP ALL;"
                
            drop_extensions = run_sparql_query(sparql, 
                                               namespace=self.def_ns,
                                               mode="update")

            # render the extensions with the base URL
            # must use a ***NON FLASK*** routing since flask is not completely
            # initiated
            rdf_resource_templates = []
            rdf_data = []
            for path, files in self.def_files.items():
                for template in files:
                    rdf_data.append(
                        render_without_request(
                            template,
                            path,
                            base_url=self.base_url))
                    rdf_resource_templates.append({template:path})
            # load the extensions in the triplestore
            context_uri = "http://knowledgelinks.io/ns/application-framework/"
            for i, data in enumerate(rdf_data):
                lg.info("uploading file: %s",
                        list(rdf_resource_templates[i])[0]) 
                data_type = list(rdf_resource_templates[i])[0].split('.')[-1]
                result = run_sparql_query(data, 
                                          mode="load",
                                          data_type=data_type,
                                          graph=self.def_graph,
                                          namespace=self.def_ns)
                if result.status_code > 399:
                    raise ValueError("Cannot load extensions {} into {}".format(
                        rdf_resource_templates[i], self.triplestore_url))

    def _set_rdf_def_filelist(self):
        ''' does a directory search for rdf application definition files '''
        def_files = {}
        latest_mod = 0
        for root, dirnames, filenames in os.walk(self.root_file_path):
            if "rdfw-definitions" in root or "custom" in root:
                filenames = [x for x in filenames if x.endswith('ttl') or \
                             x.endswith("xml") or x.endswith("nt") or \
                             x.endswith("rdf")]
                def_files[root] = filenames
                for def_file in filenames:
                    file_mod = os.path.getmtime(os.path.join(root,def_file))
                    if file_mod > latest_mod:
                        latest_mod = file_mod
        self.last_def_mod = latest_mod
        self.def_files = def_files
        json_mod = 0
        if os.path.isdir(CFG.JSON_LOCATION):
            for root, dirnames, filenames in os.walk(CFG.JSON_LOCATION):
                for json_file in filenames:
                    file_mod = os.path.getmtime(os.path.join(root,json_file))
                    if file_mod > json_mod:
                        json_mod = file_mod
        self.last_json_mod = json_mod

# Theses imports are placed at the end of the module to avoid circular imports
# from .rdfclass import RdfClass
#from rdfframework import RdfDataType

def verify_server_core(timeout=120, start_delay=90):
    ''' checks to see if the server_core is running

        args:
            delay: will cycle till core is up.
            timeout: number of seconds to wait
    '''
    timestamp = time.time()
    last_check = time.time() + start_delay - 10
    last_delay_notification = time.time() - 10
    server_down = True
    return_val = False
    timeout += 1
    # loop until the server is up or the timeout is reached
    while((time.time()-timestamp) < timeout) and server_down:
        # if delaying, the start of the check, print waiting to start
        if start_delay > 0 and time.time() - timestamp < start_delay \
                and (time.time()-last_delay_notification) > 5:
            print("Delaying server status check until %ss. Current time: %ss" \
                    % (start_delay, int(time.time() - timestamp)))
            last_delay_notification = time.time()
        # send a request check every 10s until the server is up
        while ((time.time()-last_check) > 10) and server_down:
            print("Checking status of servers at %ss" % \
                    int((time.time()-timestamp)))
            last_check = time.time()
            try:
                repo = requests.get(CFG.REPOSITORY_URL)
                repo_code = repo.status_code
                print ("\t", CFG.REPOSITORY_URL, " - ", repo_code)
            except:
                repo_code = 400
                print ("\t", CFG.REPOSITORY_URL, " - DOWN")
            try:
                triple = requests.get(CFG.TRIPLESTORE_URL)
                triple_code = triple.status_code
                print ("\t", CFG.TRIPLESTORE_URL, " - ", triple_code)
            except:
                triple_code = 400
                print ("\t", CFG.TRIPLESTORE_URL, " - down")
            if repo_code == 200 and triple_code == 200:
                server_down = False
                return_val = True
                print("**** Servers up at %ss" % \
                    int((time.time()-timestamp)))
                break
    return return_val
