import requests
from wtforms.validators import InputRequired, Email, URL, Length, EqualTo, \
        Optional
from wtforms import ValidationError
from rdfframework import RdfDataType, get_framework as rdfw
from rdfframework.utilities import make_triple, iri, clean_iri, fw_config,\
    make_list, uri, get_attr, is_not_null

__author__ = "Mike Stabile, Jeremy Nelson"
DEBUG = True
def get_wtform_validators(field):
    ''' reads the list of validators for the field and returns the wtforms
        validator list'''
    _field_validators = []
    required = field.get('kds_required', False)
    if required:
        _field_validators.append(InputRequired())
    else:
        _field_validators.append(Optional())
    _validator_list = make_list(field.get('kds_validators', []))
    for _validator in _validator_list:
        _validator_type = _validator['rdf_type']
        if _validator_type == 'kdr_PasswordValidator':
            _field_validators.append(
                EqualTo(
                    field.get("kds_formFieldName", '') +'_confirm',
                    message='Passwords must match'))
        if _validator_type == 'kdr_EmailValidator':
            _field_validators.append(Email(message=\
                    'Enter a valid email address'))
        if _validator_type == 'kdr_UrlValidator':
            _field_validators.append(URL(message=\
                    'Enter a valid URL/web address'))
        if _validator_type == 'kdr_UniqueValueValidator':
            _field_validators.append(UniqueValue())
        if _validator_type == 'kdr_StringLengthValidator':
            _string_params = _validator.get('kds_parameters')
            _param_list = _string_params.split(',')
            _param_obj = {}
            for _param in _param_list:
                _new_param = _param.split('=')
                _param_obj[_new_param[0]] = _new_param[1]
            _field_min = int(_param_obj.get('min', 0))
            _field_max = int(_param_obj.get('max', 1028))
            _field_validators.append(Length(
                min=_field_min,
                max=_field_max,
                message="{} size must be between {} and {} characters".format(
                    field.get("formFieldName"),
                    _field_min,
                    _field_max)))
    return _field_validators


class UniqueValue(object):
    ''' a custom validator for use with wtforms
        * checks to see if the value already exists in the triplestore'''

    def __init__(self, message=None):
        if not message:
            message = u'The field must be a unique value'
        self.message = message

    def __call__(self, form, field):
        # get the test query
        if not DEBUG:
            debug = False
        else:
            debug = False
        if debug: print("START UniqueValue.call rdfvalidators.py ----------\n")
        _sparql = self._make_unique_value_qry(form, field)
        if debug: print(_sparql)
        # run the test query
        _unique_test_results = requests.post(\
                fw_config().get('TRIPLESTORE_URL'),
                data={"query": _sparql, "format": "json"})
        _unique_test = _unique_test_results.json().get('results').get( \
                            'bindings', [])
        # evaluate the results; True result in the query denotes that the
        # value already exists
        if len(_unique_test) > 0:
            _unique_test = _unique_test[0].get(\
                    'uniqueValueViolation', {}).get('value', False)
        else:
            _unique_test = False
        if debug: print("END UniqueValue.call rdfvalidators.py ----------\n")
        if _unique_test:
            raise ValidationError(self.message)


    def _make_unique_value_qry(self, form, field):
        debug = False
        _sparql_args = []
        # determine the property and class details of the field
        _prop_uri = field.kds_propUri
        _class_uri = field.kds_classUri
        _range = field.rdfs_range

        # make the base triples for the query
        if _prop_uri:
            check_val = str(field.data).lower()
            _data_value = RdfDataType(None,
                                      class_uri=_class_uri,
                                      prop_uri=_prop_uri).sparql(check_val)
            _sparql_args.append(make_triple("?uri", "a", iri(uri(_class_uri))))
            _sparql_args.append(make_triple("?uri",
                                            iri(uri(_prop_uri)),
                                            _data_value))
        # see if the form is based on a set of triplestore data. if it is
        # remove that triple from consideration in the query

        if hasattr(form, "data_subject_uri"):
            _subject_uri = form.data_subject_uri
            _lookup_class_uri = form.data_class_uri
            # if the subject class is the same as the field class
            if _lookup_class_uri == _class_uri and _subject_uri:
                _sparql_args.append("FILTER(?uri!={}) .".format(\
                        iri(_subject_uri)))
            if debug: x=y
            # If not need to determine how the subject is related to the field
            # property
            elif _subject_uri:
                # class links shows the relationship between the classes in a form
                _class_links = form.dependancies
                _linked_lookup_class_uri = None
                # cycle through the class links to find the subject linkage
                for _rdf_class in _class_links:
                    for _prop in _class_links[_rdf_class]:
                        if _lookup_class_uri == _prop.get("kds_classUri"):
                            _linked_lookup_class_uri = _rdf_class
                            _linked_lookup_prop = _prop.get("kds_propUri")
                            break
                # if there is a direct link between the subject class and
                # field class add the sparql arguments
                if _linked_lookup_class_uri == _class_uri:
                    _sparql_args.append(\
                            "OPTIONAL{{?uri {} ?linkedUri}} .".format(\
                                    iri(uri(_linked_lookup_prop))))
                else:
                    # find the indirect linkage i.e.
                    #    field in class A that links to class B with a lookup
                    #    subject in class C
                    for _rdf_class in _class_links:
                        for _prop in _class_links[_rdf_class]:
                            if _class_uri == _prop.get("kds_classUri"):
                                _linked_field_class_uri = _rdf_class
                                _linked_field_prop = _prop.get("kds_propUri")
                                break
                    if _linked_lookup_class_uri == _linked_field_class_uri:
                        _sparql_args.append("OPTIONAL {")
                        _sparql_args.append("?pass {} ?uri .".format(\
                                iri(uri(_linked_field_prop))))
                        _sparql_args.append("?pass {} ?linkedUri .".format(\
                                iri(uri(_linked_lookup_prop))))
                        _sparql_args.append("} .")
                _sparql_args.append(\
                        "BIND(IF(bound(?linkedUri),?linkedUri,'') AS ?link)")
                _sparql_args.append("FILTER(?link!={}).".format(\
                        iri(_subject_uri)))
        return '''{}\nSELECT (COUNT(?uri)>0 AS ?uniqueValueViolation)
{{\n{}\n}}\nGROUP BY ?uri'''.format(rdfw().get_prefix(),
                                    "\n\t".join(_sparql_args))

class OldPasswordValidator(object):
    ''' a custom validator for use with wtforms
        * checks to see if the value already exists in the triplestore'''

    def __init__(self, message=None, **kwargs):
        if kwargs.get("tied_field_name"):
            self.tied_field_name = kwargs.get("tied_field_name")
        else:
            self.tied_field_name = None
        if not message:
            message = u'The supplied credentials are not valid!'
        self.message = message

    def __call__(self, form, field):
        # get the test query
        if not DEBUG:
            debug = False
        else:
            debug = False
        if debug: print("START OldPasswordValidator.call rdfvalidators.py --n")
        # find the username
        for fld in form.rdf_field_list:
            if fld.kds_propUri == "kds_userName":
                _username = fld
        if not is_not_null(field.data):
            if self.tied_field_name:
                tied_field = get_attr(form, self.tied_field_name)
                data = get_attr(tied_field, "data")
                if is_not_null(data):
                    raise ValidationError(self.message)
        else:
            query_data = rdfw().get_obj_data(form,
                                             lookup_related=True,
                                             processor_mode="verify")
            if len(query_data.get('query_data')) == 0:
                query_data = rdfw().get_obj_data(form,
                                               subject_lookup=_username,
                                               lookup_related=True,
                                               processor_mode="verify")
            if not field.password_verified:
                if hasattr(_username, "errors"):
                    _username.errors.append(" ")
                else:
                    setattr(_username, "errors", [" "])
                raise ValidationError(self.message)

