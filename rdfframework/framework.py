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

from werkzeug.datastructures import MultiDict
from flask import json

from .rdfproperty import RdfProperty
from rdfframework.getframework import fw_config
from rdfframework.utilities import iri, is_not_null, make_list
from rdfframework.utilities import remove_null, clean_iri, convert_spo_to_dict, convert_ispo_to_dict, \
        render_without_request, create_namespace_obj, \
        convert_obj_to_rdf_namespace, pyuri, nouri, pp, iris_to_strings, \
        JSON_LOCATION, convert_obj_to_rdf_namespace, convert_spo_def, \
        make_class
from rdfframework.processors import clean_processors, run_processor

from rdfframework.sparql import get_data, get_linker_def_item_data, \
        get_class_def_item_data, run_sparql_query, create_tstore_namespace
from rdfframework.validators import OldPasswordValidator
from rdfframework.security import User, get_app_security
from rdfframework.forms import rdf_framework_form_factory

MODULE_NAME = os.path.basename(inspect.stack()[0][1])

class RdfFramework(object):
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
    
    def __init__(self, root_file_path, **kwargs):
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        self.root_file_path = root_file_path
        self._set_rdf_def_filelist()
        self.form_list = {}
        # if the the definition files have been modified since the last json
        # files were saved reload the definition files
        if kwargs.get('reset',False) or self.last_def_mod > self.last_json_mod:
            reset = True
        else:
            reset = False
        if not os.path.isdir(JSON_LOCATION):
            print("JSON cache directory not found.\nCreating directory")
            reset = True
            os.makedirs(JSON_LOCATION)
        if not os.path.exists(os.path.join(JSON_LOCATION, "app_query.json")):
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
            self._generate_classes(reset)
            self._generate_linkers(reset)
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
        result = requests.post(fw_config().get('TRIPLESTORE_URL'),
                                 data={"query": self.get_prefix() + sparql,
                                       "format": "json"})
        value = result.json().get('results', {}).get('bindings', [])
        if len(value) == 0:
            # if not loaded save the data
            data_list = make_list(fw_config().get('FRAMEWORK_DEFAULT'))
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
                                url=fw_config().get("TRIPLESTORE_URL"),
                                headers={"Content-Type":
                                         "text/turtle"},
                                data=save_query)

    def user_authentication(self, rdf_obj):
        ''' reads the object for authentication information and sets the
            flask userclass information '''

        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        # find the username and password
        for fld in rdf_obj.rdf_field_list:
            if fld.kds_propUri == "kds_userName":
                _username = fld
            if fld.kds_propUri == "kds_password":
                _password = fld
        # get the stored information
        subject_lookup = _username
        query_data = self.get_obj_data(rdf_obj,
                                       subject_lookup=_username,
                                       lookup_related=True,
                                       processor_mode="verify")
        if _password.password_verified:
            user_obj = self._make_user_obj(rdf_obj, query_data, _username)

            #login_user(new_user)
            #print(current_user.is_authenticated())
            #print("framework ------------ ", current_user.is_authenticated)
            #pp.pprint(current_user.__dict__)
            #pp.pprint(current_app.__dict__)

            #current_app.login_manager.login_user(new_user)

            if user_obj.get("change_password") is True:
                rdf_obj.save_state = "password_reset"
            else:
                rdf_obj.save_state = "success"
                new_user = User(user_obj)
                rdf_obj.save_results = new_user

        else:
            error_msg = "The supplied credentials could not be verified"
            _username.errors.append(" ")
            _password.errors.append(error_msg)
            rdf_obj.save_state = "fail"

    def clear_password_reset(self, rdf_obj):
        ''' reads through the rdf_obj fields/data and changes the
            kds_changePasswordRequired property to false '''
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        for fld in rdf_obj.rdf_field_list:
            if fld.kds_propUri == "kds_userName":
                _username = fld
            if fld.kds_propUri == "kds_password":
                for validator in make_list(fld.validators):
                    lg.debug(validator)
                    if isinstance(validator, OldPasswordValidator):
                        _password = fld
        # get the stored information
        subject_lookup = _username
        query_data = self.get_obj_data(rdf_obj,
                                       subject_lookup=_username,
                                       lookup_related=True,
                                       processor_mode="verify")
        if _password.password_verified:
            for subject, value in query_data['query_data'].items():
                if iri(rdf_obj.data_class_uri) in \
                        make_list(value.get("rdf_type")):
                    rdf_obj.subject_uri = subject
            req_fld = None
            for fld in rdf_obj.rdf_field_list:
                if fld.kds_propUri == "kds_changePasswordRequired":
                    req_fld = fld
                    fld.data = False
            if req_fld is None:
                prop_json = self.kds_UserClass.kds_properties.get(\
                        "kds_changePasswordRequired")
                prop_json['kds_classUri'] = "kds_UserClass"
                prop_json['name'] = "pw_reset_req"
                req_fld = RdfProperty(prop_json, False)
                rdf_obj.add_props([req_fld])
            self.save_obj(rdf_obj, query_data)
            user_obj = self._make_user_obj(rdf_obj, query_data, _username)
            rdf_obj.save_state = "success"
            new_user = User(user_obj)
            rdf_obj.save_results = new_user

    def _make_user_obj(self, rdf_obj, query_data, username):
        ''' This method will create a user_obj dictionary to be used when
            initializing a User() for the login_manager '''
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
            
        person_info = None
        user_obj = {}
        user_uri = ""
        user_groups = []
        for subject, value in query_data['query_data'].items():
            person_class = iri(self.app.get("kds_personClass","schema_Person"))
            rdf_types = make_list(value.get("rdf_type"))
            if person_class in rdf_types:
                person_info = value
                person_uri = subject
            elif "<kds_UserClass>" in rdf_types:
                user_info = value
                user_uri = subject
            elif "<kds_UserGroup>" in rdf_types:
                user_groups.append(subject)
        if person_info:
            user_obj = {'username': username.data,
                        'email': person_info['schema_email'],
                        'full_name': "%s %s" % (\
                                person_info['schema_givenName'],
                                     person_info['schema_familyName']),
                        'person_uri': person_uri,
                        'change_password': \
                                user_info.get('kds_changePasswordRequired',True),
                        'user_uri': user_uri,
                        'user_groups': user_groups,
                        'app_security': get_app_security(self, user_groups)}
        lg.debug("user_obj:\n%s", json.dumps(user_obj, indent=4))
        return user_obj

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

    def save_object_with_subobj(self, rdf_obj, old_data=None):
        ''' finds the subform field and appends the parent form attributes
           to the subform entries and individually sends the augmented
           subform to the main save_form property'''
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        _parent_fields = []
        _parent_field_list = {}
        result = []
        rdf_obj.save_results = []
        rdf_obj.save_state = "success"
        if self.log_level == logging.DEBUG:
            debug_data = []
            debug_data.append("name\t\tdata\t\tfield")
            debug_data.append("---------------------")
            for fld in rdf_obj.Recipient.entries[0].form.rdf_field_list:
                debug_data.append("%s\t\t%s\t\t%s" % (fld.name, fld.data, fld))
            debug_data.append("---------------------")
            for fld in rdf_obj.Recipient.entries[1].form.rdf_field_list:
                debug_data.append("%s\t\t%s\t\t%s" % (fld.name, fld.data, fld))
            debug_data.append("---------------------")
            for fld in rdf_obj.Recipient.entries[2].form.rdf_field_list:
                debug_data.append("%s\t\t%s\t\t%s" % (fld.name, fld.data, fld))
            lg.debug("\n".join(debug_data))
        for _field in rdf_obj.rdf_field_list:
            if _field.type != 'FieldList':
                _parent_fields.append(_field)
            else:
                _parent_field_list = rdf_obj.rdf_field_list[:].remove(_field)
        for _field in rdf_obj.rdf_field_list:
            if _field.type == 'FieldList':
                for _entry in _field.entries:
                    if _entry.type == 'FormField':
                        if hasattr(_entry.form,"subjectUri"):
                            _entry.form.data_subject_uri = \
                                    _entry.form.subjectUri.data
                            _entry.form.data_class_uri = \
                                    _entry.form.subjectUri.kds_classUri
                            _entry.form.remove_prop(_entry.form.subjectUri)

                            # ------------------------------------------
                            debug_note = []
                            for fld in _entry.form.rdf_field_list:
                                debug_note.append("%s - %s | %s" % \
                                        (fld.name, fld.data, fld))
                            for fld in _field.entries[2].form.rdf_field_list:
                                debug_note.append("%s - %s | %s" % \
                                        (fld.name, fld.data, fld))
                            lg.debug("\nsubjectUri: %s\n%s",
                                    _entry.form.subjectUri.data,
                                    "\n".join(debug_note))
                            # -------------------------------------------

                        _entry.form.add_props(_parent_fields)
                        save_result = self.save_obj(_entry.form, old_data)
                        rdf_obj.save_results.append(save_result)
                        if _entry.form.save_state is not "success":
                            rdf_obj.save_state = "fail"
        rdf_obj.save_subject_uri = rdf_obj.data_subject_uri
        return {"success":True, "results":result}

    def save_obj(self, rdf_obj, old_data=None):
        ''' Recieves RDF_formfactory form, validates and saves the data

         *** Steps ***
         - determine if subform is present
         - group fields by class
         - validate the form data for class requirements
         - determine the class save order. classes with no dependant properties
           saved first
         - send data to classes for processing
         - send data to classes for saving
        '''
        
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        

        if old_data is None:
            old_obj_data = self.get_obj_data(rdf_obj)
            rdf_obj.query_data = old_obj_data.get('query_data')
        else:
            old_obj_data = old_data
        lg.debug("\nold_obj_data\n%s", pp.pformat(old_obj_data))
        if rdf_obj.has_subobj:
            return self.save_object_with_subobj(rdf_obj, old_obj_data)
        if rdf_obj.is_subobj:

            missing_data = {}
            for class_uri, dep_prop_list in rdf_obj.reverse_dependancies.items():
                for dep_prop in dep_prop_list:
                    for prop in rdf_obj.rdf_field_list:
                        if prop.kds_propUri == dep_prop.get("kds_propUri") \
                                and class_uri != rdf_obj.data_class_uri:
                            if is_not_null(prop.data):
                                new_data = self.get_obj_data(rdf_obj, subject_uri = \
                                        prop.data, class_uri=class_uri)
                                q_data_list = make_list(new_data.get('query_data'))
                                for q_data in q_data_list:
                                    if q_data and len(q_data)>0:
                                        if isinstance(q_data, dict):
                                            for sub, data in q_data.items():
                                                if iri(class_uri) in make_list(data.get('rdf_type')):
                                                    missing_data.update({sub:data})
            old_obj_data['query_data'].update(missing_data)
        rdf_obj.set_obj_data(query_data=old_obj_data['query_data'])
        #print("~~~~~~~~~ _old_form_data: ", _old_form_data)
        # validate the form data for class requirements (required properties,
        # security, valid data types etc)

        _validation = self._validate_obj_by_class_reqs(rdf_obj)
        if not _validation.get('success'):
            rdf_obj.reset_fields()
            print("%%%%%%% validation in save_form\n", pp.pformat(_validation))
            return _validation
        # determine class save order
        _form_by_classes = rdf_obj.class_grouping
        _class_save_order = self._get_save_order(rdf_obj)

        lg.debug("class save order:\n%s", pp.pformat(_class_save_order))

        _reverse_dependancies = rdf_obj.reverse_dependancies
        _id_class_uri = rdf_obj.data_class_uri
        # save class data
        _data_results = []
        id_value = None
        for _rdf_class in _class_save_order:
            _status = {}
            _status = getattr(self, _rdf_class).save(rdf_obj)
            _data_results.append({"rdfClass":_rdf_class, "status":_status})
            lg.debug("status ----------\n%s", pp.pformat(_status))
            if _status.get("status") == "success":
                _update_class = _reverse_dependancies.get(_rdf_class, [])
                if _rdf_class == _id_class_uri:
                    id_value = clean_iri(\
                            _status.get("lastSave", {}).get("objectValue"))
                for _prop in _update_class:
                    found = False
                    for i, field in enumerate(
                            rdf_obj.class_grouping.get(_prop.get('kds_classUri', ''))):
                        if field.kds_propUri ==  _prop.get('kds_propUri'):
                            found = True
                            _form_by_classes[field.kds_classUri][i].data = \
                                _status.get("lastSave", {}).get("objectValue")
                            _form_by_classes[field.kds_classUri][i].editable = \
                                    True
                    if not found:
                        prop_json = getattr(self, _prop.get('kds_classUri')\
                                ).kds_properties.get(_prop.get('kds_propUri'))
                        prop_json['kds_classUri'] = _prop.get('kds_classUri')
                        data = _status.get("lastSave", {}).get("objectValue")
                        new_prop = RdfProperty(prop_json, data)

                        _form_by_classes[_prop.get('kds_classUri')].append(\
                                new_prop)
        rdf_obj.save_state = "success"
        rdf_obj.save_subject_uri = id_value
        rdf_obj.save_results = _data_results
        return  rdf_obj

    def get_prefix(self, format_type="sparql"):
        ''' Generates a string of the rdf namespaces listed used in the
            framework

            formatType: "sparql" or "turtle"
        '''
        return self.ns_obj.prefix(format_type)

    def get_class_links(self, set_of_classes):
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        _class_set = set()
        _dependant_classes = set()
        _independant_classes = set()
        _class_dependancies = {}
        _reverse_dependancies = {}
        _class_set = remove_null(_class_set)
        # cycle through all of the rdf classes
        for _rdf_class in set_of_classes:
            # get the instance of the RdfClass
            _current_class = getattr(self, _rdf_class)
            _current_class_dependancies = _current_class.list_dependant()
            # add the dependant properties to the class depenancies dictionay
            _class_dependancies[_rdf_class] = _current_class_dependancies
            for _reverse_class in _current_class_dependancies:
                if not isinstance(_reverse_dependancies.get(_reverse_class.get(\
                        "kds_classUri", "missing")), list):
                    _reverse_dependancies[_reverse_class.get("kds_classUri", \
                            "missing")] = []
                _reverse_dependancies[\
                        _reverse_class.get("kds_classUri", "missing")].append(\
                                {"kds_classUri":_rdf_class,
                                 "kds_propUri":_reverse_class.get("kds_propUri", "")})
            if len(_current_class.list_dependant()) > 0:
                _dependant_classes.add(_current_class.kds_classUri)
            else:
                _independant_classes.add(_current_class.kds_classUri)
        return {"dep_classes": list(_dependant_classes),
                "indep_classes" : list(_independant_classes),
                "dependancies" : _class_dependancies,
                "reverse_dependancies" : _reverse_dependancies}

    def get_obj_data(self, rdf_obj, **kwargs):
        ''' returns the data for the current form paramters
        **keyword arguments
        subject_uri: the URI for the subject
        class_uri: the rdf class of the subject
        '''

        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        _class_uri = kwargs.get("class_uri", rdf_obj.data_class_uri)
        subject_uri = kwargs.get("subject_uri", rdf_obj.data_subject_uri)
        _subobj_data = {}
        _data_list = kwargs.get("data_list",False)
        _parent_field = None
        processor_mode = kwargs.get("processor_mode","load")
        #x = y #kds:lookupPropertyUri kds:userName;
        subject_lookup = kwargs.get("subject_lookup", kwargs.get("id_value"))
        # if there is no subject_uri exit the function
        if not is_not_null(subject_uri) and not subject_lookup:
            return {'query_data':{}}
        # test to see if a subobj is in the form
        if rdf_obj.has_subobj:
            _sub_rdf_obj_list = []
            # find the subform fields
            for _field in rdf_obj.rdf_field_list:
                if _field.type == 'FieldList':
                    if getattr(_field.entries[0],'type') == 'FormField':
                        for _entry in _field.entries:
                            _sub_rdf_obj = _entry.form
                            _sub_rdf_obj.is_subobj = True
                            _sub_rdf_obj_list.append(_sub_rdf_obj)
            # if subforms exist, recursively call this method to get the
            # subform data
            _subobj_datalist = []
            for _sub_rdf_obj in _sub_rdf_obj_list:
                _subobj_datalist.append(self.get_obj_data(_sub_rdf_obj,
                    subject_uri=subject_uri, class_uri=_class_uri))
        _query_data = convert_spo_to_dict(convert_obj_to_rdf_namespace(\
                    get_data(rdf_obj, **kwargs)), "subject", rdf_obj.xsd_load)
        rdf_obj.query_data = _query_data
        lg.debug("\n_query_data\n%s", pp.pformat(_query_data))
        # compare the return results with the form fields and generate a
        # formData object

        _obj_data_list = []
        for _item in make_list(_query_data):
            _obj_data = {}
            for _prop in rdf_obj.rdf_field_list:
                data = read_prop_data(_prop, rdf_obj, _item, processor_mode)   
                i = 0
                if len(data) > 1 or _prop.type == "FieldList":
                    for _value in data:
                        _obj_key = "%s-%s" % (_prop.kds_formFieldName, i)
                        _obj_data[_obj_key] = _value
                        i = i + 1
                elif len(data) == 1:
                    _obj_data[_prop.kds_formFieldName] = data[0]
            _obj_data_list.append(MultiDict(_obj_data))
        if len(_obj_data_list) == 1:
            _obj_data_dict = _obj_data_list[0]
        elif len(_obj_data_list) > 1:
            _obj_data_dict = _obj_data_list
        else:
            _obj_data_dict = MultiDict()
        _obj_data = iris_to_strings(_obj_data)
        lg.debug(pp.pformat({"obj_data":_obj_data_dict,
                             "obj_json":_obj_data,
                             "query_data":_query_data,
                             "form_class_uri":_class_uri}))
        return {"obj_data":_obj_data_dict,
                "obj_json":_obj_data,
                "query_data":_query_data,
                "form_class_uri":_class_uri}

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
            if fw_config().get("DEFAULT_RDF_NS"):
                self.ns_obj.dict_load(fw_config()['DEFAULT_RDF_NS'])
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

    def _generate_classes(self, reset):
        ''' generates a python RdfClass for each defined rdf class in
            the app vocabulary '''
        if self.class_initialized != True:
            _class_json = self._load_rdf_class_defintions(reset)
            self.rdf_class_dict = convert_obj_to_rdf_namespace(_class_json,
                                                               self.ns_obj)
            print("\t\t%s objects" % len(self.rdf_class_dict))
            self.class_initialized = True
            kds_saveLocation = self.app.get("kds_saveLocation","triplestore")
            kds_subjectPattern = self.app.get("kds_subjectPattern",
                    "!--baseUrl,/,ns,/,!--classPrefix,/,!--className,/,!--uuid")
            #for rdfclass, value in self.rdf_class_dict.items():
            #    self.rdf_class_dict[rdfclass]['kds_properties'] = \
            #        make_list(self.rdf_class_dict[rdfclass]['kds_properties'])
            for _rdf_class in self.rdf_class_dict:    
                setattr(self,
                        _rdf_class,
                        RdfClass(self.rdf_class_dict[_rdf_class],
                                 _rdf_class,
                                 kds_saveLocation=kds_saveLocation,
                                 kds_subjectPattern=kds_subjectPattern))

    def _generate_linkers(self, reset):
        ''' generates a python RdfClass for each defined rdf class in
            the app vocabulary '''
        if self.linkers_initialized != True:
            _linkers_json = self._load_rdf_linker_defintions(reset)
            self.rdf_linker_dict = _linkers_json
            print("\t\t%s objects" % len(self.rdf_linker_dict))
            self.linkers_initialized = True
            
    def _generate_forms(self, reset):
        ''' adds the dictionary of form definitions as an attribute of
            this class. The form python class uses this dictionary to
            create a python form class at the time of calling. '''
        if self.forms_initialized != True:
            _form_json = self._load_rdf_form_defintions(reset)
            self.rdf_form_dict = convert_obj_to_rdf_namespace(_form_json,
                                                              self.ns_obj)
            for rdfform, value in self.rdf_form_dict.items():
                self.rdf_form_dict[rdfform]['kds_properties'] = \
                    make_list(self.rdf_form_dict[rdfform]['kds_properties'])
            print("\t\t%s objects" % len(self.rdf_form_dict))
            self._make_form_list()
            self.form_initialized = True

    def _generate_apis(self, reset):
        ''' adds the dictionary of api definitions as an attribute of
            this class. The api python class uses this dictionary to
            create a python api class at the time of calling. '''
        if self.apis_initialized != True:
            _api_json = self._load_rdf_api_defintions(reset)
            self.rdf_api_dict = convert_obj_to_rdf_namespace(_api_json,
                                                              self.ns_obj)
            for api, value in self.rdf_api_dict.items():
                self.rdf_api_dict[api]['kds_properties'] = \
                    make_list(self.rdf_api_dict[api]['kds_properties'])
            print("\t\t%s objects" % len(self.rdf_api_dict))
            self._make_api_list()
            self.apis_initialized = True

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
                os.path.join(JSON_LOCATION, "app_query.json"),
                "w") as file_obj:
                file_obj.write( _string_defs )
            print("end write")
            _json_defs = json.loads(_string_defs)
            print("end load")
        else:
            with open(
                os.path.join(JSON_LOCATION, "app_query.json")) as file_obj:
                _json_defs = json.loads(file_obj.read())
        return _json_defs

    def _load_rdf_class_defintions(self, reset):
        ''' Queries the triplestore for list of classes used in the app as
            defined in the rdfw-definitions folders'''
        print("\tLoading rdf class definitions")
        if reset:
            # get a list of all of the rdf classes being defined
            prefix = self.ns_obj.prefix()
            graph = fw_config().get('RDF_DEFINITION_GRAPH')
            sparql = render_without_request("sparqlClassDefinitionList.rq",
                                             graph=graph,
                                             prefix=prefix)
            class_qry = requests.post(fw_config().get('TRIPLESTORE_URL'),
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
                os.path.join(JSON_LOCATION,"class_query.json"),
                "w") as file_obj:
                file_obj.write( json.dumps(class_dict, indent=4) )
        else:
            with open(
                os.path.join(JSON_LOCATION, "class_query.json")) as file_obj:
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
                os.path.join(JSON_LOCATION,"linker_query.json"),
                "w") as file_obj:
                file_obj.write(json.dumps(linker_dict, indent=4))
        else:
            with open(
                os.path.join(JSON_LOCATION, "linker_query.json")) as file_obj:
                linker_dict = json.loads(file_obj.read())
        return linker_dict

    def _load_rdf_form_defintions(self, reset):
        ''' Queries the triplestore for list of forms used in the app as
            defined in the kl_app.ttl file'''
        print("\tLoading form definitions")
        if reset:
            _sparql = render_without_request("jsonFormQueryTemplate.rq",
                                             graph=fw_config().get(\
                                                    'RDF_DEFINITION_GRAPH'))
            _form_list = requests.post(fw_config().get('TRIPLESTORE_URL'),
                                       data={"query": _sparql, "format": "json"})
            _raw_json = _form_list.json().get('results').get('bindings'\
                    )[0]['appForms']['value']
            _string_defs = _raw_json.replace('hasProperty":', 'properties":')

            with open(
                os.path.join(JSON_LOCATION, "form_query.json"),
                "w") as file_obj:
                file_obj.write( _string_defs)
            _json_defs = json.loads(_string_defs)
        else:
            with open(
                os.path.join(JSON_LOCATION, "form_query.json")) as file_obj:
                _json_defs = json.loads(file_obj.read())
        return _json_defs

    def _load_rdf_api_defintions(self, reset):
        ''' Queries the triplestore for list of forms used in the app as
            defined in the kl_app.ttl file'''
        print("\tLoading api definitions")
        if reset:
            _sparql = render_without_request("jsonApiQueryTemplate.rq",
                                             graph=fw_config().get(\
                                                    'RDF_DEFINITION_GRAPH'))
            _api_list = requests.post(fw_config().get('TRIPLESTORE_URL'),
                                       data={"query": _sparql, "format": "json"})
            _raw_json = _api_list.json().get('results').get('bindings'\
                    )[0]['appApis']['value']
            _string_defs = _raw_json.replace('hasProperty":', 'properties":')
            _json_defs = json.loads(_string_defs)
            with open(
                os.path.join(JSON_LOCATION, "api_query.json"),
                "w") as file_obj:
                file_obj.write( _string_defs )
        else:
            with open(
                os.path.join(JSON_LOCATION, "api_query.json")) as file_obj:
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

    def _get_save_order(self, rdf_obj):
        '''Cycle through the classes and determine in what order they need
           to be saved
           1. Classes who's properties don't rely on another class
           2. Classes that that depend on classes in step 1
           3. Classes stored as blanknodes of Step 2 '''

        _save_order = []
        _save_last = []
        for _rdf_class in rdf_obj.indep_classes:
            _save_order.append(_rdf_class)
        for _rdf_class in rdf_obj.dep_classes:
            _dependant = True
            for _dep_class in rdf_obj.dependancies:
                if _dep_class != _rdf_class:
                    for _prop in rdf_obj.dependancies.get(_dep_class, []):
                        #print(_class_name, " d:", _dep_class, " r:", _rdf_class, " p:",
                              #_prop.get('classUri'))
                        if _prop.get('kds_classUri') == _rdf_class:
                            _dependant = False
            if not _dependant:
                _save_order.append(_rdf_class)
            else:
                _save_last.append(_rdf_class)
        return _save_order + _save_last

    def _load_rdf_data(self, reset=False):
        ''' loads the RDF/turtle application data to the triplestore '''
        
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        
        
        self.base_url = fw_config().get('ORGANIZATION').get('url',"")
        self.ts = fw_config().get('TRIPLESTORE', {})
        self.def_config = fw_config().get('RDF_DEFINITIONS')
        self.triplestore_url = self.ts['url']
        self.def_ns = self.def_config.get('namespace',
                                          self.ts.get("default_ns", "kb"))
        create_tstore_namespace(self.def_ns)
        create_tstore_namespace(self.ts['default_ns'])
        # Strip off trailing forward slash for TTL template
        if self.base_url.endswith("/"):
            self.base_url = self.base_url[:-1]
        # if the extensions exist in the triplestore drop the graph
        self.def_graph = clean_iri(self.def_config.get('graph',
                self.ts.get('default_graph', "")))
        if reset:
            if self.def_config['method'] == "graph":
                sparql = "DROP GRAPH %s;" % def_config['graph'] 
                graph = clean_iri(self.def_config['graph'])
            elif self.def_config['method'] == "namespace":
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
            #self.def_graph = rdflib.Graph()
            for i, data in enumerate(rdf_data):
                lg.info("uploading file: %s",
                        list(rdf_resource_templates[i])[0]) 
                result = run_sparql_query(data, 
                                          mode="load",
                                          graph=self.def_graph,
                                          namespace=self.def_ns)
                # file_path = "".join([os.path.join(value, key) for key, value in rdf_resource_templates[i].items()])
                # try:
                #     self.def_graph.parse(file_path, format='turtle')
                # except:
                #     print("Error loading: ", file_path)
                if result.status_code > 399:
                    raise ValueError("Cannot load extensions {} into {}".format(
                        rdf_resource_templates[i], self.triplestore_url))
            #print(len(self.def_graph))

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
        if os.path.isdir(JSON_LOCATION):
            for root, dirnames, filenames in os.walk(JSON_LOCATION):
                for json_file in filenames:
                    file_mod = os.path.getmtime(os.path.join(root,json_file))
                    if file_mod > json_mod:
                        json_mod = file_mod
        self.last_json_mod = json_mod

# Theses imports are placed at the end of the module to avoid circular imports
from .rdfclass import RdfClass
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
                repo = requests.get(fw_config().get('REPOSITORY_URL'))
                repo_code = repo.status_code
                print ("\t", fw_config().get('REPOSITORY_URL'), " - ", repo_code)
            except:
                repo_code = 400
                print ("\t", fw_config().get('REPOSITORY_URL'), " - DOWN")
            try:
                triple = requests.get(fw_config().get('TRIPLESTORE_URL'))
                triple_code = triple.status_code
                print ("\t", fw_config().get('TRIPLESTORE_URL'), " - ", triple_code)
            except:
                triple_code = 400
                print ("\t", fw_config().get('TRIPLESTORE_URL'), " - down")
            if repo_code == 200 and triple_code == 200:
                server_down = False
                return_val = True
                print("**** Servers up at %ss" % \
                    int((time.time()-timestamp)))
                break
    return return_val


def read_prop_data(prop, rdf_obj, qry_data, processor_mode):

    prop_uri = prop.kds_propUri
    _class_uri = prop.kds_classUri
    _data_value = None
    if not hasattr(prop, 'kds_fieldType'):
        _field_type = {}
    else:
        _field_type = prop.kds_fieldType
    if "subform" in _field_type.get("rdf_type",'').lower():
        #! NEED _subform_data
        return []
        for i, _data in enumerate(make_list(\
                _subform_data.get("obj_data"))):
            for _key, _value in _data.items():
                _obj_key = "%s-%s-%s" % (prop.kds_formFieldName,
                                         i,
                                        _key)
                _obj_data[_obj_key] = _value
        return _old_data
    else:
        prop_query_data = None
        # find the prop class_uri's query_data
        prop_old_data = get_class_qry_data(_class_uri, prop_uri, qry_data) 
        _data_value = prop_old_data
        
        return_list = []
        for list_data in prop_old_data: 
            return_list.append(process_prop(prop, 
                                            rdf_obj, 
                                            processor_mode, 
                                            list_data))

        return return_list
        

def get_class_qry_data(class_uri, prop_uri, qry_data):
    ''' Function reads through the query data and returns the specified 
        class data 
        
        Args:
            class_uri - the rdf:Class searched for
            qry_data - the query data to search through 
            
        Returns:
            list of qry_data dictionaries
    '''
    lg = logging.getLogger("%s.%s" % (MODULE_NAME, inspect.stack()[0][3]))
    lg.setLevel(logging.INFO)
    
    class_uri = iri(class_uri)
    return_list = []
    if class_uri not in [None, "kds_NoClass"]:
        for _subject in qry_data:
            lg.debug("******* %s - %s", 
                     class_uri,
                     qry_data.get(_subject, {}).get("rdf_type"))
            if class_uri in qry_data.get(_subject,{}).get("rdf_type"):
                return_list.append(qry_data[_subject].get(prop_uri))
    return return_list
  
def process_prop(prop, rdf_obj, processor_mode, prop_query_data):
    ''' This will run the processors attached to prop and return the processed
        data:
        
        Args:
            prop: the property to processe
            rdf_obj: the form/api obj 
            processor_mode: which mode to run the processors in
        
        Returns:
            the processed data
    '''
    lg = logging.getLogger("%s.%s" % (MODULE_NAME, inspect.stack()[0][3]))
    lg.setLevel(logging.INFO)
    
    return_val = None
    for _processor in clean_processors([make_list(prop.kds_processors)],
                                       prop.kds_classUri).values():
        run_processor(_processor, rdf_obj, prop, processor_mode)
    if prop.kds_propUri == "kds_StaticValue":
        prop.processed_data = prop.kds_returnValue
        return_val = prop.kds_returnValue
    if prop.processed_data is not None:
        lg.debug("\n%s __ %s --pro-- %s ",
                 prop.kds_propUri, type(prop), 
                 prop.processed_data)
        return_val = prop.processed_data
        prop.processed_data = None
    else:
        return_val = prop_query_data              
    return return_val
