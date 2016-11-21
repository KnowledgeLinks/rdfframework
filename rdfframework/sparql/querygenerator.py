import os
import requests
import copy
import json
import pdb

try:
    from rdfframework import get_framework as rdfw
    from rdfframework.utilities import make_triple, iri, uri,\
            is_not_null, render_without_request, make_list, pp, uid_to_repo_uri, \
            RdfNsManager as NS_MGR, convert_spo_to_dict, make_class
except ImportError:
    # Try local import
    from .. import get_framework as rdfw
    from ..utilities import make_triple, iri, uri,\
            is_not_null, render_without_request, make_list, pp, uid_to_repo_uri, \
            RdfNsManager as NS_MGR, make_class
   
from instance import config as cf
config = make_class(cf.__dict__)

DEBUG = True

NSM = NS_MGR(config=config)
def get_data(obj, **kwargs):
    ''' queries that datastore for the based on the supplied arguments '''
    _sparql = create_data_sparql_query(obj, **kwargs)
    data = run_sparql_query(_sparql, **kwargs)
    return data

def create_tstore_namespace(namespace_name, **kwargs):
    """ will send a request to the triplestore to create a new namespace

    Args:
        namespace_name: the name of the new namespace
    """
    data = render_without_request("namespace_quads_template.xml",
                                  ns_name=namespace_name)
    return requests.post(headers={"Content-Type":"application/xml"}, 
                         data=data,
                         url=config.TRIPLESTORE.ns_url)

def delete_tstore_namespace(namespace_name, **kwargs):
    """ will send a request to the triplestore to delete a namespace

    Args:
        namespace_name: the name of the namespace
    """
    url = os.path.join(config.TRIPLESTORE.ns_url,
                       namespace_name).replace("\\","/")
    return requests.delete(url=url)


def run_sparql_query(sparql, mode='get', **kwargs):
    """ run the passed in sparql query and returns the results 

    Args:
        spaqrl: the sparl query to run. If a prefix is not provided one will be
                attached
    kwargs:
        mode: ['get','update','load']
        namespace: the triplestore namespace to use
        graph: used with 'load' to define the graph to load data to
    """
    if mode == 'load':
        _prefix = NSM.prefix("turtle")
    else:
        _prefix = NSM.prefix()
    if sparql is not None:
        query = sparql
        if not (sparql.lower().startswith("prefix") or \
                sparql.lower().startswith("@prefix")):
            query = "\n".join([_prefix, sparql])
    else:
        return None
    sparql_endpoint = config.TRIPLESTORE.url
    

    if kwargs.get("namespace"):
        sparql_endpoint = os.path.join(sparql_endpoint.replace("sparql",""),
                                       "namespace",
                                       kwargs['namespace'],
                                       "sparql").replace("\\","/")
    if mode == "get":
        _results = requests.post(sparql_endpoint,
                                 data={"query": query,
                                       "format": "json"})
        if _results:
            return _results.json().get('results', {}).get('bindings', [])
        else:
            return []
    elif mode == "update":
        return requests.post(sparql_endpoint, data={"update":query})
    elif mode == "load":
        context_uri = kwargs.get("graph",
                                 config.TRIPLESTORE.default_graph)
        return requests.post(url=sparql_endpoint,
                             headers={"Content-Type": "text/turtle"},
                             params={"context-uri": context_uri},
                             data=sparql)


def create_data_sparql_query(obj, **kwargs):
    ''' generates the sparql query for getting an object's data '''
    if not DEBUG:
        debug = False
    else:
        debug = True
    if debug: print("START create_data_sparql_query -----------------------\n")
    if debug: print("*** kwargs ***: \n%s \n*** obj ***:\n%s" %
            (pp.pformat(kwargs), pp.pformat(obj.__dict__)))
    from rdfframework import RdfDataType
    subject_uri = kwargs.get("subject_uri", obj.data_subject_uri)
    _class_uri = kwargs.get("class_uri", obj.data_class_uri)
    _formated_val = None
    _lookup_triple = ""
    if obj.rdf_instructions.get("kds_subjectUriTransform"):
        if obj.rdf_instructions.get("kds_subjectUriTransform") == \
                "kdr_UidToRepositoryUri":
            id_value = kwargs.get("id_value")
            if kwargs.get("id_value"):
                _subject_uri = uid_to_repo_uri(id_value)
                subject_uri = _subject_uri
                obj.data_subject_uri = _subject_uri
        elif obj.rdf_instructions.get("kds_subjectUriTransform") == \
                "kdr_UidToTriplestoreUri":
            id_value = kwargs.get("id_value")
            if kwargs.get("id_value"):
                rdf_class = getattr(rdfw(), obj.data_class_uri)
                subject_uri = rdf_class.uri_patterner(id_value)
                obj.data_subject_uri = subject_uri

    elif kwargs.get("id_value") or obj.rdf_instructions.get("kds_lookupPropertyUri"):
        # find the details for formating the sparql query for the supplied
        # id_value or lookup via a property Value
        id_value = kwargs.get("id_value")
        if not id_value:
            id_value = subject_uri
        _kds_propUri = obj.rdf_instructions.get("kds_lookupPropertyUri")
        _rdf_class_uri = obj.rdf_instructions.get("kds_lookupPropertyClass")
        if not _rdf_class_uri:
            _rdf_class_uri = obj.rdf_instructions.get("kds_lookupClassUri")
        _rdf_class = getattr(rdfw(),_rdf_class_uri)
        _rdf_prop = _rdf_class.kds_properties[_kds_propUri]
        _range = make_list(_rdf_prop.get("rdfs_range"))[0]
        _formated_val = RdfDataType(_range.get("rangeClass")).sparql(id_value)
        _lookup_triple = "\t{}\n\t{}\n\t".format(
                make_triple("?subject",
                            "a",
                            iri(uri(_rdf_class.kds_classUri))),
                make_triple("?subject",
                            iri(uri(_kds_propUri)),
                            _formated_val))
        subject_uri = "?subject"

    subject_lookup = kwargs.get("subject_lookup")
    if subject_lookup:
        # subject lookup will pull a subject and all of its related data
        _kds_propUri = iri(uri(subject_lookup.kds_propUri))
        _data_type = uri(make_list(subject_lookup.rdfs_range)[0])
        _prop_value = RdfDataType(_data_type).sparql(\
                str(subject_lookup.data))
        _sparql = render_without_request("sparqlRelatedItemDataTemplate.rq",
                                         prefix=rdfw().get_prefix(),
                                         kds_propUri=_kds_propUri,
                                         prop_value=_prop_value)
        if debug: print(_sparql)
        if debug: print("END create_data_sparql_query -----Related-Lookup--\n")   
        return _sparql
    _lookup_class_uri = _class_uri
    _sparql_args = None
    _sparql_constructor = copy.deepcopy(obj.dependancies)
    if debug:
        print("+++++++++++++++++++++++ Dependancies:")
        pp.pprint(_sparql_constructor)
    _base_subject_finder = None
    _linked_class = None
    _linked_prop = False
    _sparql_elements = []
    _subform_data = {}
    _data_list = obj.is_subobj
    _parent_field = None
    if is_not_null(subject_uri):
        # find the primary linkage between the supplied subjectId and
        # other form classes

        for _rdf_class in _sparql_constructor:
            for _prop in _sparql_constructor[_rdf_class]:
                try:
                    if _class_uri == _prop.get("kds_classUri"):
                        _sparql_args = _prop
                        _linked_class = _rdf_class
                        _sparql_constructor[_rdf_class].remove(_prop)
                        if _rdf_class != _lookup_class_uri:
                            _linked_prop = True
                except:
                    pass
        # generate the triple pattern for linked class
        if debug:
            print("+++++++++++++++++++++++ SPARQL Constructor")
            pp.pprint(_sparql_constructor)
        if _sparql_args:
            # create a binding for multi-item results
            if _data_list:
                _list_binding = "BIND(?classID AS ?itemID) ."
            else:
                _list_binding = ''
            # provide connection triples for the id subject and associated
            # rdf class
            format_string = "{}BIND({} AS ?baseSub) .\n\t{}\n\t{}\n\t{}"
            _base_subject_finder = format_string.format(
                        _lookup_triple,
                        iri(subject_uri),
                        make_triple("?baseSub",
                                    "a",
                                    iri(uri(_lookup_class_uri))),
                        make_triple("?classID",
                                    iri(uri(_sparql_args.get("kds_propUri"))),
                                    "?baseSub"),
                        _list_binding)
           # if there is a linkage between subject_uri and another associated
           # property in object
            if _linked_prop:
                # create a binding for multi-item results
                if _data_list:
                    _list_binding = "BIND(?s AS ?itemID) ."
                else:
                    _list_binding = ''
                format_string = \
                        "{}BIND({} AS ?baseSub) .\n\t{}\n\t{}\n\t{}\n\t?s ?p ?o ."
                _sparql_elements.append(format_string.format(\
                                _lookup_triple,
                                iri(subject_uri),
                                make_triple("?baseSub",
                                            "a",
                                            iri(uri(_lookup_class_uri))),
                                make_triple("?s",
                                            iri(uri(_sparql_args.get("kds_propUri"))),
                                            "?baseSub"),
                                _list_binding))
        # iterrate though the classes used in the object and generate the
        # spaqrl triples to pull the data for that class
        for _rdf_class in _sparql_constructor:
            if _rdf_class == _class_uri:
                if _data_list:
                    _list_binding = "BIND(?s AS ?itemID) ."
                else:
                    _list_binding = ''
                if is_not_null(_lookup_triple) and is_not_null(_list_binding):
                    format_string = \
                            "{}BIND({} AS ?basesub).\n\t{}\n\t{}\n\t{}\n\t?s ?p ?o ."
                    _sparql_elements.append(format_string.format(
                            _lookup_triple,
                            iri(subject_uri),
                            make_triple('?baseSub','a',iri(uri(_lookup_class_uri))),
                            make_triple('?classID',iri(uri(_sparql_args.get("kds_propUri"))),'?s'),
                            "BIND(?classID AS ?itemID) ."))
                else:
                    format_string = \
                                "\t{}BIND({} AS ?s) .\n\t{}\n\t{}\n\t?s ?p ?o ."
                    _sparql_elements.append(format_string.format(
                                _lookup_triple,
                                iri(subject_uri),
                                make_triple("?s", "a", iri(uri(_lookup_class_uri))),
                                _list_binding))
            for _prop in _sparql_constructor[_rdf_class]:
                if _rdf_class == _class_uri:
                    if _data_list:
                        _list_binding = "BIND(?s AS ?itemID) ."
                    else:
                        _list_binding = ''
                    format_string = \
                                "\t{}BIND({} AS ?baseSub) .\n\t{}\n\t{}\n\t{}\n\t?s ?p ?o ."
                    _sparql_arg = format_string.format(\
                            _lookup_triple,
                            iri(subject_uri),
                            make_triple("?baseSub",
                                        "a",
                                        iri(uri(_lookup_class_uri))),
                            make_triple("?baseSub",
                                        iri(uri(_prop.get("kds_propUri"))),
                                        "?s"),
                            _list_binding)
                    _sparql_elements.append(_sparql_arg)
                elif _rdf_class == _linked_class:
                    _sparql_elements.append(
                        "\t{}\n\t{}\n\t?s ?p ?o .".format(
                            _base_subject_finder,
                            make_triple("?classID",
                                        iri(uri(_prop.get("kds_propUri"))),
                                        "?s")
                            )
                        )


                '''**** The case where an ID looking up a the triples for
                    a non-linked related is not functioning i.e. password
                    ClassID not looking up person org triples if the org
                    class is not used in the form. This may not be a
                    problem ... the below comment out is a start to solving
                     if it is a problem

                    elif _linked_class != self.get_class_name(prop.get(\
                            "classUri")):
                    _sparql_elements.append(
                        "\t" +_base_subject_finder + "\n " +
                        "\t"+ make_triple("?classID", iri(prop.get(\
                                "propUri")), "?s") + "\n\t?s ?p ?o .")'''

        # merge the sparql elements for each class used into one combined
        # sparql union statement
        _sparql_unions = "{{\n{}\n}}".format("\n} UNION {\n".join(\
                _sparql_elements))
        if _data_list:
            _list_binding = "?itemID"
        else:
            _list_binding = ''
        # render the statment in the jinja2 template
        _sparql = render_without_request("sparqlItemTemplate.rq",
                                         prefix=rdfw().get_prefix(),
                                         query=_sparql_unions,
                                         list_binding=_list_binding)
        if debug:
            print("SPARQL query")
            print(_sparql)
        if debug: print("END create_data_sparql_query ---------------------\n")
        return _sparql

def query_select_options(field):
    ''' returns a list of key value pairs for a select field '''
    _prefix = rdfw().get_prefix()
    _select_query = field.kds_fieldType.get('kds_selectQuery', None)
    _select_list = {}
    _options = []
    if _select_query:
        # send query to triplestore
        _select_list = requests.post(
            config.TRIPLESTORE_URL,
            data={"query": _prefix + _select_query,
                  "format": "json"})
        _raw_options = _select_list.json().get('results', {}).get('bindings', [])
        _bound_var = field.kds_fieldType.get('kds_selectBoundValue', ''\
                ).replace("?", "")
        _display_var = field.kds_fieldType.get('kds_selectDisplay', ''\
                ).replace("?", "")
        # format query result into key value pairs
        for row in _raw_options:
            _options.append(
                {
                    "id":iri(row.get(_bound_var, {}).get('value', '')),
                    "value":row.get(_display_var, {}).get('value', '')
                })
    return _options

def save_file_to_repository(data, repo_item_address):
    ''' saves a file from a form to a repository'''
    object_value = ""
    if repo_item_address:
        print("~~~~~~~~ write code here")
    else:
        repository_result = requests.post(
            config.REPOSITORY_URL,
            data=data.read(),
			         headers={"Content-type":"'image/png'"})
        object_value = repository_result.text
    return iri(object_value)

def get_all_item_data(item_uri):
    _sparql = render_without_request("sparqlAllItemDataTemplate.rq",
                                     prefix=NSM.prefix(),
                                     item_uri=item_uri)
    return run_sparql_query(_sparql)

def get_class_def_item_data(class_uri, **kwargs):
    definition_graph = kwargs.get("definition_graph",
                                  config.RDF_DEFINITIONS.graph)
    _sparql = render_without_request("sparqlClassDefinitionDataTemplate.rq",
                                     prefix=NSM.prefix(),
                                     item_uri=class_uri,
                                     graph=definition_graph)
    return run_sparql_query(_sparql, namespace=kwargs.get("namespace","kb")) 

def get_linker_def_item_data(**kwargs):
    definition_graph = kwargs.get("definition_graph",
                                  config.RDF_DEFINITIONS.graph)
    if not definition_graph:
        definition_graph = "bd:nullGraph"
    sparql = render_without_request("sparqlLinkerDefinitionDataTemplate.rq",
                                     prefix=NSM.prefix(),
                                     definition_graph=definition_graph)
    if kwargs.get("def_graph"):
        return kwargs['def_graph'].query(_sparql)
    else:
        return run_sparql_query(_sparql, namespace=kwargs.get("namespace","kb"))    
