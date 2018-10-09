"""Python RDF Mapping Language Processor

>>> import bibcat.rml.processor as processor

"""

__author__ = "Jeremy Nelson"

# Standard Python Modules
import collections
import csv
import datetime
import os
import sys
from types import SimpleNamespace
import pdb, pprint
import logging
import json
# 3rd party modules
import rdflib
import requests

import jsonpath_ng
# import bibcat
# from bibcat.maps import get_map

from rdfframework.datatypes import RdfNsManager, BaseRdfDataType, Uri
from rdfframework.connections import setup_conn, Blazegraph, RdflibConn, \
        make_tstore_conn
from rdfframework.sparql import get_all_item_data
from rdfframework.datasets import RdfDataset
from rdfframework.utilities import pick, KeyRegistryMeta
from rdfframework.datatypes import Uri
from .rmlmanager import RmlManager

BIBCAT_BASE = os.path.abspath(
    os.path.split(
        os.path.dirname(__file__))[0])
NS_MGR = RdfNsManager()
RML_MGR = RmlManager()
PREFIX = None
# __version__ = bibcat.__version__

try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

class Processor(object, metaclass=KeyRegistryMeta):
    __required_idx_attrs__ = {'rdf_name', '__name__'}

    """
    Base class for RDF Mapping Language Processors, child classes
    encapsulate different types of Data sources

    Attributes:
        rml: Graph of RML rules
        ext_conn: Triplestore connection used for querying and saving data
        use_json_qry: If the RML mapping has the json mapping that will be
            used instead of the full SPARQL query to the database
        ds: RdfDataset used for json_qry of the data

    """

    def __init__(self, rml_rules, **kwargs):
        # log.setLevel(logging.DEBUG)
        self.__setup_conn__(**kwargs)
        self.use_json_qry = False
        self.default_use_json_qry = False
        self.rml = rdflib.Graph()
        if isinstance(rml_rules, list):
            for rule in rml_rules:
                # First check if rule exists on the filesystem
                # pdb.set_trace()
                if os.path.exists(rule):
                    with open(rule) as file_obj:
                        raw_rule = file_obj.read()
                else:
                    raw_rule = RML_MGR.get_rml(rule, 'data').decode()
                self.rml.parse(data=raw_rule,
                               format='turtle')
        elif isinstance(rml_rules, (rdflib.Graph, rdflib.ConjunctiveGraph)):
            self.rml = rml_rules
        elif os.path.exists(rml_rules):
            self.rml.parse(rml_rules, format='turtle')
        else:
            self.rml.parse(data=RML_MGR.get_rml(rml_rules).decode(),
                           format='turtle')
        # Populate Namespaces Manager
        for prefix, namespace in self.rml.namespaces():
            NS_MGR.bind(prefix, namespace, ignore_errors=True)
        self.source, self.triplestore_url = None, None
        self.parents = set()
        self.constants = dict(version=kwargs.get("version", "Not Defined"))
        self.triple_maps = dict()
        for row in self.rml.query(GET_TRIPLE_MAPS):
            triple_map_iri = row[0]
            map_key = str(triple_map_iri)
            self.triple_maps[map_key] = SimpleNamespace()
            self.triple_maps[map_key].logicalSource = \
                self.__logical_source__(triple_map_iri)
            self.triple_maps[map_key].subjectMap = \
                self.__subject_map__(triple_map_iri)
            self.triple_maps[map_key].predicateObjectMap = \
                self.__predicate_object_map__(triple_map_iri)
        self.set_context()
        self.set_list_predicates()

    def __graph__(self):
        """
        Method returns a new graph with all of the namespaces in
        RML graph
        """

        graph = rdflib.Graph()
        for prefix, name in self.rml.namespaces():
            graph.namespace_manager.bind(prefix, name)
        return graph

    def __setup_conn__(self, **kwargs):
        """
        Sets the ext_conn based on the kwargs.

        returns a triplestore conncection based on the kwargs.
        Order of preceedence is as follows:
            kwargs['conn']
            kwargs['tstore_def']
            kwargs['triplestore_url']
            kwargs['rdflib']
            RdfConfigManager.data_tstore
            RdfConfigManager.TRIPLESTORE_URL

        kwargs:
            conn: established triplestore connection object
            tstore_def: dictionary of paramaters specifying the connection as
                    outlined in the config file
            triplestore_url: url to a triplestore. A blazegraph connection
                will be used if specified
            rdflib: defintion for an rdflib connection
        """
        self.ext_conn = setup_conn(**kwargs)

    def __generate_delimited_objects__(self, output, **kwargs):
        """
        Internal methods takes a subject, predicate, element, and a list
        of delimiters that are applied to element's text and a triples
        for each value is created and associated with the subject.

        Keyword Args:

        -------------
            triple_map: SimpleNamespace
            predicate: URIRef
            element: XML Element
            datatype: XSD Datatype, optional
            delimiters: List of delimiters to apply to string
        """
        triple_map = kwargs.get("triple_map")
        subject = kwargs.get('subject')
        # Subject is blank-node, try to retrieve subject IRI
        predicate = kwargs.get('predicate')
        element = kwargs.get('element')
        datatype = kwargs.get('datatype', None)
        delimiters = kwargs.get('delimiters')
        subjects = []
        for delimiter in delimiters:
            values = element.text.split(delimiter)
            for row in values:
                if datatype is not None:
                    obj_ = rdflib.Literal(row.strip(), datatype=datatype)
                else:
                    obj_ = rdflib.Literal(row.strip())
                if isinstance(subject, rdflib.BNode):
                    new_subject = rdflib.BNode()
                    class_ = triple_map.subjectMap.class_
                    output.add((new_subject, NS_MGR.rdf.type.rdflib, class_))
                    for parent_subject, parent_predicate in \
                            output.subject_predicates(object=subject):
                        output.add((parent_subject,
                                         parent_predicate,
                                         new_subject))
                else:
                    new_subject = subject
                subjects.append(new_subject)
                output.add((new_subject, predicate, obj_))
        return subjects

    def __generate_reference__(self, triple_map, **kwargs):
        """Placeholder method, should be extended by child classes

        Args:

        -----
            triple_map: SimpleNamespace

        Keyword Args:

        -------------
        """
        pass

    def __generate_object_term__(self, datatype, value):
        """Internal method takes a datatype (can be None) and returns
        the RDF Object Term

        Args:

        -----
            datatype: None, or rdflib.URIRef
            value: Varys depending on ingester
        """
        if datatype == NS_MGR.xsd.anyURI.rdflib:
            term = rdflib.URIRef(value)
        elif datatype:
            term = rdflib.Literal(value, datatype=datatype)
        else:
            term = rdflib.Literal(value)
        return term

    def __handle_parents__(self, output, **kwargs):
        """Internal method handles parentTriplesMaps

        Keyword args:

        -------------

            parent_map: SimpleNamespace of ParentTriplesMap
            subject: rdflib.URIRef or rdflib.BNode
            predicate: rdflib.URIRef
        """
        parent_map = kwargs.pop("parent_map")
        subject = kwargs.pop('subject')
        predicate = kwargs.pop('predicate')
        parent_objects = self.execute(
            self.triple_maps[str(parent_map)],
            output,
            **kwargs)
        for parent_obj in parent_objects:
            if isinstance(parent_obj, BaseRdfDataType):
                parent_obj = parent_obj.rdflib
            if parent_obj == subject:
                continue
            output.add((
                subject,
                predicate,
                parent_obj))

    def __logical_source__(self, map_iri):
        """Creates a SimpleNamespace for the TripelMap's logicalSource

        Args:

        -----
            map_iri: URIRef
        """
        # pdb.set_trace()
        logical_source = SimpleNamespace()
        logical_src_bnode = self.rml.value(
            subject=map_iri,
            predicate=NS_MGR.rml.logicalSource.rdflib)
        if logical_src_bnode is None:
            return
        logical_source.source = self.rml.value(
            subject=logical_src_bnode,
	        predicate=NS_MGR.rml.source.rdflib)
        logical_source.reference_formulations = [r for r in self.rml.objects(
            subject=logical_src_bnode,
            predicate=NS_MGR.rml.referenceFormulation.rdflib)]
        logical_source.iterator = self.rml.value(
            subject=logical_src_bnode,
            predicate=NS_MGR.rml.iterator.rdflib)
        query = self.rml.value(
            subject=logical_src_bnode,
            predicate=NS_MGR.rml.query.rdflib)
        json_query = self.rml.value(
            subject=logical_src_bnode,
            predicate=NS_MGR.rml.reference.rdflib)
        json_key = self.rml.value(
            subject=logical_src_bnode,
            predicate=NS_MGR.rml.key.rdflib)
        if query is not None:
            logical_source.query = query
        if json_query is not None:
            self.use_json_qry = True
            self.default_use_json_qry = True
            logical_source.json_query = json_query
            logical_source.json_key = json_key
        return logical_source

    def __subject_map__(self, map_iri):
        """Creates a SimpleNamespace for the TripleMap's subjectMap and
        populates properties from the RML RDF graph

        Args:

        -----
            map_iri: rdflib.URIRef,TripleMap IRI

        Returns:

        --------
            SimpleNamespace
        """
        subject_map = SimpleNamespace()
        subject_map_bnode = self.rml.value(
            subject=map_iri,
            predicate=NS_MGR.rr.subjectMap.rdflib)
        if subject_map_bnode is None:
            return
        #! Should look at supporting multiple rr:class definitions
        subject_map.class_ = self.rml.value(
            subject=subject_map_bnode,
            predicate=getattr(NS_MGR.rr, "class").rdflib)
        subject_map.template = self.rml.value(
            subject=subject_map_bnode,
            predicate=NS_MGR.rr.template.rdflib)
        subject_map.termType = self.rml.value(
            subject=subject_map_bnode,
            predicate=NS_MGR.rr.termType.rdflib)
        subject_map.deduplicate = self.rml.value(
            subject=subject_map_bnode,
            predicate=NS_MGR.kds.deduplicate.rdflib)
        subject_map.reference = self.rml.value(
            subject=subject_map_bnode,
            predicate=NS_MGR.rr.reference.rdflib)
        return subject_map

    def __predicate_object_map__(self, map_iri):
        """Iterates through rr:predicateObjectMaps for this TripleMap
        creating a SimpleNamespace for each triple map and assigning the
        constant, template, parentTripleMap, reference as properties.

        Args:

        -----
                map_iri:  rdflib.URIRef, TripleMap IRI

        Returns:

        --------
                list:  List of predicate_object Namespace objects
        """
        pred_obj_maps = []
        for pred_obj_map_bnode in self.rml.objects(
                subject=map_iri,
                predicate=NS_MGR.rr.predicateObjectMap.rdflib):
            pred_obj_map = SimpleNamespace()
            pred_obj_map.predicate = self.rml.value(
                subject=pred_obj_map_bnode,
                predicate=NS_MGR.rr.predicate.rdflib)
            obj_map_bnode = self.rml.value(
                subject=pred_obj_map_bnode,
                predicate=NS_MGR.rr.objectMap.rdflib)
            if obj_map_bnode is None:
                continue
            pred_obj_map.constant = self.rml.value(
                subject=obj_map_bnode,
                predicate=NS_MGR.rr.constant.rdflib)
            pred_obj_map.template = self.rml.value(
                subject=obj_map_bnode,
                predicate=NS_MGR.rr.template.rdflib)
            pred_obj_map.parentTriplesMap = self.rml.value(
                subject=obj_map_bnode,
                predicate=NS_MGR.rr.parentTriplesMap.rdflib)
            if pred_obj_map.parentTriplesMap is not None:
                self.parents.add(str(pred_obj_map.parentTriplesMap))
            pred_obj_map.reference = self.rml.value(
                subject=obj_map_bnode,
                predicate=NS_MGR.rr.reference.rdflib)
            pred_obj_map.datatype = self.rml.value(
                subject=obj_map_bnode,
                predicate=NS_MGR.rr.datatype.rdflib)
            pred_obj_map.query = self.rml.value(
                subject=obj_map_bnode,
                predicate=NS_MGR.rml.query.rdflib)
            pred_obj_map.json_query = self.rml.value(
                subject=obj_map_bnode,
                predicate=NS_MGR.rml.reference.rdflib)
            json_key = None
            if hasattr(self.triple_maps[str(map_iri)].logicalSource,
                       'json_key'):
                json_key = self.triple_maps[str(map_iri)].logicalSource.json_key
            pred_obj_map.json_key = pick(self.rml.value(
                    subject=obj_map_bnode,
                    predicate=NS_MGR.rml.key.rdflib),
                    json_key)
            # BIBCAT Extensions
            pred_obj_map.delimiters = []
            if pred_obj_map.json_query:
                self.use_json_qry = True
            for obj in self.rml.objects(subject=obj_map_bnode,
                                        predicate=NS_MGR.kds.delimiter.rdflib):
                pred_obj_map.delimiters.append(obj)
            pred_obj_maps.append(pred_obj_map)
        return pred_obj_maps

    def add_to_triplestore(self, output):
        """Method attempts to add output to Blazegraph RDF Triplestore"""
        if len(output) > 0:
            result = self.ext_conn.load_data(data=output.serialize(),
                                             datatype='rdf')

    def generate_term(self, **kwargs):
        """Method generates a rdflib.Term based on kwargs"""
        term_map = kwargs.pop('term_map')
        if hasattr(term_map, "termType") and\
            term_map.termType == NS_MGR.rr.BlankNode.rdflib:
            return rdflib.BNode()
        if not hasattr(term_map, 'datatype'):
            term_map.datatype = NS_MGR.xsd.anyURI.rdflib
        if hasattr(term_map, "template") and term_map.template is not None:
            template_vars = kwargs
            template_vars.update(self.constants)
            # Call any functions to generate values
            for key, value in template_vars.items():
                if hasattr(value, "__call__"):
                    template_vars[key] = value()
            raw_value = term_map.template.format(**template_vars)
            if term_map.datatype == NS_MGR.xsd.anyURI.rdflib:
                return rdflib.URIRef(raw_value)
            return rdflib.Literal(raw_value,
                                  datatype=term_map.datatype)
        if term_map.reference is not None:
            # Each child will have different mechanisms for referencing the
            # source based
            return self.__generate_reference__(term_map, **kwargs)

    def execute(self, triple_map, **kwargs):
        """Placeholder method should be overridden by child classes"""
        raise NotImplemented("Execute Method required in subclass.")

    def run(self, **kwargs):
        """Run method iterates through triple maps and calls the execute
        method"""
        if 'timestamp' not in kwargs:
            kwargs['timestamp'] = datetime.datetime.utcnow().isoformat()
        if 'version' not in kwargs:
            kwargs['version'] = "Not Defined" #bibcat.__version__
        # log.debug("kwargs: %s", pprint.pformat({k:v for k, v in kwargs.items()
        #                                         if k != "dataset"}))
        # log.debug("parents: %s", self.parents)
        for map_key, triple_map in self.triple_maps.items():
            if map_key not in self.parents:
                self.execute(triple_map, **kwargs)

    def set_context(self):
        """
        Reads throught the namespaces in the RML and generates a context for
        json+ld output when compared to the RdfNsManager namespaces
        """
        results = self.rml.query("""
                SELECT ?o {
                    {
                        ?s rr:class ?o
                    } UNION {
                        ?s rr:predicate ?o
                    }
                }""")
        namespaces = [Uri(row[0]).value[0]
                      for row in results
                      if isinstance(row[0], rdflib.URIRef)]
        self.context = {ns[0]: ns[1] for ns in namespaces if ns[0]}

    def set_list_predicates(self):
        """
        Reads through the rml mappings and determines all fields that should
        map to a list/array with a json output
        """
        results = self.rml.query("""
                SELECT DISTINCT ?subj_class ?list_field
                {
                    ?bn rr:datatype rdf:List .
                    ?bn rr:predicate ?list_field .
                    ?s ?p ?bn .
                    ?s rr:subjectMap ?sm_bn .
                    ?sm_bn rr:class ?subj_class .
                }""")
        list_preds = [(Uri(row[0]).sparql, Uri(row[1]).sparql)
                      for row in results]
        array_fields = {}
        for tup in list_preds:
            try:
                array_fields[tup[0]].append(tup[1])
            except KeyError:
                array_fields[tup[0]] = [tup[1]]
        self.array_fields = array_fields

    def __call__(self, **kwargs):
        output = self.run(**kwargs)
        rtn_format = kwargs.get("rtn_format")
        if rtn_format:
            if rtn_format == "json-ld":
                result = self.json_ld(output, **kwargs)
                # pdb.set_trace()
                return result
            else:
                return output.serialize(format=rtn_format).decode()

        return output

    def json_ld(self, output, **kwargs):
        """
        Returns the json-ld formated result
        """
        raw_json_ld = output.serialize(format='json-ld',
                                       context=self.context).decode()
        # if there are fields that should be returned as arrays convert all
        # non-array fields to an array
        if not self.array_fields:
            return raw_json_ld
        json_data = json.loads(raw_json_ld)
        for i, item in enumerate(json_data['@graph']):
            if item.get("@type") in self.array_fields:
                test_flds = self.array_fields[item['@type']]
                for key, val in item.items():
                    if key in test_flds and not isinstance(val, list):
                        json_data['@graph'][i][key] = [val]
        # print(json.dumps(json_data, indent=4))
        return json.dumps(json_data, indent=4)

class CSVProcessor(Processor):
    """CSV RDF Mapping Processor"""
    rdf_name = Uri("kds:RmlCSVPRocessor")

    def __init__(self, **kwargs):
        if "fields" in kwargs:
            self.fields = kwargs.pop("fields")
        if "rml_rules" in kwargs:
            rml_rules = kwargs.pop("rml_rules")
        csv_file = kwargs.pop("csv_file")
        self.reader = csv.DictReader(open(csv_file, 'rb'))
        super(CSVProcessor, self).__init__(rml_rules, **kwargs)

    def __generate_reference__(self, triple_map, **kwargs):
        """Extracts the value of either column by key or by position """
        pass

    def execute(self, triple_map, **kwargs):
        """Method executes mapping between CSV source and
        output RDF

        args:
            triple_map(SimpleNamespace): Triple Map
        """
        pass

    def run(self, **kwargs):
        """Method runs through CSV Reader and applies rules to each
        row.

        """
        pass

class CSVRowProcessor(Processor):
    """RML Processor for CSV/TSV or other delimited file supported by the
    python standard library module csv"""
    rdf_name = Uri("kdr:RmlCSVRowProcessor")

    def __init__(self, **kwargs):
        if "rml_rules" in kwargs:
            rml_rules = kwargs.pop("rml_rules")
        else:
            rml_rules = []
        super(CSVRowProcessor, self).__init__(rml_rules, **kwargs)

    def __generate_reference__(self, triple_map, **kwargs):
        """Generates a RDF entity based on triple map

        Args:
            triple_map(SimpleNamespace): Triple Map
        """
        raw_value = self.source.get(str(triple_map.reference))
        if raw_value is None or len(raw_value) < 1:
            return
        if hasattr(triple_map, "datatype"):
            if triple_map.datatype == NS_MGR.xsd.anyURI.rdflib:
                output = rdflib.URIRef(raw_value)
            else:
                output = rdflib.Literal(
                    raw_value,
                    datatype=triple_map.datatype)
        else:
            output = rdflib.Literal(raw_value)
        return output

    def execute(self, triple_map, output, **kwargs):
        """Method executes mapping between CSV source and
        output RDF

        args:
            triple_map(SimpleNamespace): Triple Map
        """
        subject = self.generate_term(term_map=triple_map.subjectMap,
                                     **kwargs)
        start_size = len(output)
        all_subjects = []
        for pred_obj_map in triple_map.predicateObjectMap:
            predicate = pred_obj_map.predicate
            if pred_obj_map.template is not None:
                object_ = self.generate_term(term_map=pred_obj_map, **kwargs)
                if len(str(object)) > 0:
                    output.add((
                        subject,
                        predicate,
                        object_))

            if pred_obj_map.parentTriplesMap is not None:
                self.__handle_parents__(
                    parent_map=pred_obj_map.parentTriplesMap,
                    subject=subject,
                    predicate=predicate,
                    **kwargs)
            if pred_obj_map.reference is not None:
                object_ = self.generate_term(term_map=pred_obj_map,
                                             **kwargs)
                if object_ and len(str(object_)) > 0:
                    output.add((subject, predicate, object_))
            if pred_obj_map.constant is not None:
                output.add((subject, predicate, pred_obj_map.constant))
        finish_size = len(output)
        if finish_size > start_size:
            output.add((subject,
                             NS_MGR.rdf.type.rdflib,
                             triple_map.subjectMap.class_))
            all_subjects.append(subject)
        return all_subjects



    def run(self, row, **kwargs):
        """Methods takes a row and depending if a dict or list,
        runs RML rules.

        Args:
        -----
            row(Dict, List): Row from CSV Reader
        """
        self.source = row
        kwargs['output'] = self.__graph__()
        super(CSVRowProcessor, self).run(**kwargs)
        return kwargs['output']

class JSONProcessor(Processor):
    """JSON RDF Mapping Processor"""
    rdf_name = Uri("kdr:RmlJSONProcessor")

    def __init__(self, **kwargs):
        try:
            rml_rules = kwargs.pop("rml_rules")
        except KeyError:
            rml_rules = []
        super(JSONProcessor, self).__init__(rml_rules, **kwargs)

    def __generate_reference__(self, triple_map, **kwargs):
        json_obj = kwargs.get("obj")
        path_expr = jsonpath_ng.parse(triple_map.reference)
        results = [r.value.strip() for r in path_expr.find(json_obj)]
        for row in results:
            if rdflib.term._is_valid_uri(row):
                return rdflib.URIRef(row)

    def __reference_handler__(self, output, **kwargs):
        """Internal method for handling rr:reference in triples map

        Keyword Args:

        -------------
            predicate_obj_map: SimpleNamespace
            obj: dict
            subject: rdflib.URIRef
        """
        subjects = []
        pred_obj_map = kwargs.get("predicate_obj_map")
        obj = kwargs.get("obj")
        subject = kwargs.get("subject")
        if pred_obj_map.reference is None:
            return subjects
        predicate = pred_obj_map.predicate
        ref_exp = jsonpath_ng.parse(str(pred_obj_map.refernce))
        found_objects = [r.value for r in ref_exp(obj)]
        for row in found_objects:
            output.add((subject, predicate, rdflib.Literal(row)))


    def execute(self, triple_map, output, **kwargs):
        """Method executes mapping between JSON source and
        output RDF

        Args:

        -----
            triple_map: SimpleNamespace
        """
        subjects = []
        logical_src_iterator = str(triple_map.logicalSource.iterator)
        json_object = kwargs.get('obj', self.source)
        # Removes '.' as a generic iterator, replace with '@'
        if logical_src_iterator == ".":
            results = [None,]
        else:
            json_path_exp = jsonpath_ng.parse(logical_src_iterator)
            results = [r.value for r in json_path_exp.find(json_object)][0]
        for row in results:
            subject = self.generate_term(term_map=triple_map.subjectMap,
                                         **kwargs)
            for pred_obj_map in triple_map.predicateObjectMap:
                predicate = pred_obj_map.predicate
                if pred_obj_map.template is not None:
                    output.add((
                        subject,
                        predicate,
                        self.generate_term(term_map=pred_obj_map, **kwargs)))

                if pred_obj_map.parentTriplesMap is not None:
                    self.__handle_parents__(
                        output,
                        parent_map=pred_obj_map.parentTriplesMap,
                        subject=subject,
                        predicate=predicate,
                        obj=row,
                        **kwargs)
                if pred_obj_map.reference is not None:
                    ref_exp = jsonpath_ng.parse(str(pred_obj_map.reference))
                    found_objects = [r.value for r in ref_exp.find(row)]
                    for obj in found_objects:
                        if rdflib.term._is_valid_uri(obj):
                            rdf_obj = rdflib.URIRef(str(obj))
                        else:
                            rdf_obj = rdflib.Literal(str(obj))
                        output.add((subject, predicate, rdf_obj))
                if pred_obj_map.constant is not None:
                    output.add((subject,
                                     predicate,
                                     pred_obj_map.constant))
            subjects.append(subject)
        return subjects

    def run(self, source, **kwargs):
        """Method takes a JSON source and any keywords and transforms from
        JSON to Lean BIBFRAME 2.0 triples

        Args:

        ----
            source: str, dict
        """
        kwargs['output'] = self.__graph__()
        if isinstance(source, str):
            import json
            source = json.loads(source)
        self.source = source
        super(JSONProcessor, self).run(**kwargs)
        self.output = kwargs['output']
        return output


class XMLProcessor(Processor):
    """XML RDF Mapping Processor"""
    rdf_name = Uri("kdr:RmlXMLProcessor")

    def __init__(self, **kwargs):
        if "rml_rules" in kwargs:
            rml_rules = kwargs.pop("rml_rules")
        super(XMLProcessor, self).__init__(rml_rules, **kwargs)
        if "namespaces" in kwargs:
            self.xml_ns = kwargs.pop("namespaces")
        else:
            self.xml_ns = dict()
        self.constants.update(kwargs)

    def __generate_reference__(self, triple_map, **kwargs):
        """Internal method takes a triple_map and returns the result of
        applying to XPath to the current DOM context

        Args:
        -----
            triple_map: SimpleNamespace
            element: etree.Element
        """
        element = kwargs.get("element")
        found_elements = element.xpath(
            triple_map.reference,
            namespaces=self.xml_ns)
        for elem in found_elements:
            raw_text = elem.text.strip()
            #! Quick and dirty test for valid URI
            if not raw_text.startswith("http"):
                continue
            return rdflib.URIRef(raw_text)


    def __reference_handler__(self, output, **kwargs):
        """Internal method for handling rr:reference in triples map

        Keyword Args:

        -------------
            predicate_obj_map: SimpleNamespace
            element: etree.Element
            subject: rdflib.URIRef
        """
        subjects = []
        pred_obj_map = kwargs.get("predicate_obj_map")
        element = kwargs.get("element")
        subject = kwargs.get("subject")
        if pred_obj_map.reference is None:
            return subjects
        predicate = pred_obj_map.predicate
        found_elements = element.xpath(
            str(pred_obj_map.reference),
            namespaces=self.xml_ns)

        for found_elem in found_elements:
            if not hasattr(pred_obj_map, "datatype") or \
                pred_obj_map.datatype is None:
                datatype = None
            else:
                datatype = pred_obj_map.datatype
            if isinstance(found_elem, str): # Handle xpath attributes
                object_ = self.__generate_object_term__(datatype, found_elem)
                output.add((subject, predicate, object_))
                continue
            if found_elem.text is None or len(found_elem.text) < 1:
                continue
            if pred_obj_map.constant is not None:
                output.add((subject,
                                 predicate,
                                 pred_obj_map.constant))
                continue
            if pred_obj_map.delimiters != []:
                subjects.extend(
                    self.__generate_delimited_objects__(
                        output,
                        triple_map=pred_obj_map,
                        subject=subject,
                        predicate=predicate,
                        element=found_elem,
                        delimiters=pred_obj_map.delimiters,
                        datatype=datatype))
            else:
                object_ = self.__generate_object_term__(datatype, found_elem.text)
                output.add((subject, predicate, object_))
        return subjects


    def execute(self, triple_map, output, **kwargs):
        """Method executes mapping between source

        Args:

        -----
            triple_map: SimpleNamespace, Triple Map

        """
        subjects = []
        found_elements = self.source.xpath(
            str(triple_map.logicalSource.iterator),
            namespaces=self.xml_ns)
        for element in found_elements:
            subject = self.generate_term(term_map=triple_map.subjectMap,
                                         element=element,
                                         **kwargs)
            start = len(output)
            for row in triple_map.predicateObjectMap:
                predicate = row.predicate
                if row.template is not None:
                    obj_ = self.generate_term(term_map=row, **kwargs)
                    output.add((subject, predicate, obj_))
                if row.parentTriplesMap is not None:
                    self.__handle_parents__(
                        output,
                        parent_map=row.parentTriplesMap,
                        subject=subject,
                        predicate=predicate,
                        **kwargs)
                new_subjects = self.__reference_handler__(
                    output,
                    predicate_obj_map=row,
                    element=element,
                    subject=subject)
                subjects.extend(new_subjects)
                if row.constant is not None:
                    output.add((subject, predicate, row.constant))
            if start < len(output):
                if triple_map.subjectMap.class_ is not None:
                    output.add((subject,
                                NS_MGR.rdf.type.rdflib,
                                triple_map.subjectMap.class_))
                subjects.append(subject)
        return subjects



    def run(self, xml, **kwargs):
        """Method takes either an etree.ElementTree or raw XML text
        as the first argument.

        Args:
            xml(etree.ElementTree or text
        """
        kwargs['output'] = self.__graph__()
        if isinstance(xml, str):
            try:
                self.source = etree.XML(xml)
            except ValueError:
                try:
                    self.source = etree.XML(xml.encode())
                except:
                    raise ValueError("Cannot run error {}".format(sys.exc_info()[0]))
        else:
            self.source = xml
        super(XMLProcessor, self).run(**kwargs)
        self.output = kwargs['output']
        return kwargs['output']

def __get_object__(binding):
    """Method takes a binding extracts value and returns rdflib
     entity

     Args:
         binding: binding row
    """
    if isinstance(binding, rdflib.term.Node):
        return binding
    elif isinstance(binding, collections.Iterable):
        for key, row in binding.items():
            if isinstance(row, (rdflib.URIRef, rdflib.Literal)):
                return row
            elif isinstance(row, dict):
                if row.get('type').startswith('uri'):
                    return rdflib.URIRef(row.get('value'))
                return rdflib.Literal(row.get('value'))
            elif isinstance(row, tuple):
                print(row)
            elif isinstance(row, str):
                if row.startswith("literal") or "xml:lang" in key:
                    continue
                return rdflib.Literal(row)

class SPARQLProcessor(Processor):
    """SPARQLProcessor provides a RML Processor for external SPARQL endpoints"""
    rdf_name = Uri("kdr:RmlSPARQLProcessor")

    def __init__(self, rml_rules, **kwargs):
        # if "rml_rules" in kwargs:
        #     rml_rules = kwargs.pop("rml_rules")
        super(SPARQLProcessor, self).__init__(rml_rules, **kwargs)
        __set_prefix__()
        #! self.triplestore = kwargs.get("triplestore", self.__graph__())

        # Sets defaults
        self.limit, self.offset = 5000, 0
        self.data_query = self.rml.value(
                subject=NS_MGR.kds.DataQuery.rdflib,
                predicate=NS_MGR.rml.query.rdflib)

    def __get_bindings__(self, sparql, output_format):
        """Internal method queries triplestore or remote
        sparql endpont and returns the bindings

        Args:

        ----
            sparql: String of SPARQL query
            output_format: String of type of outputform
        """
        return self.ext_conn.query(sparql,
                                   rtn_format=output_format,
                                   debug=False)


    def run(self, **kwargs):
        kwargs['output'] = self.__graph__()
        if "limit" in kwargs:
            self.limit = kwargs.get('limit')
        if "offset" in kwargs:
            self.offset = kwargs.get('offset')
        start = datetime.datetime.now()
        if kwargs.get("no_json"):
            self.use_json_qry = False
        else:
            self.use_json_qry = self.default_use_json_qry
        if self.use_json_qry:
            if not kwargs.get('dataset'):
                if self.data_query:
                    sparql = PREFIX + self.data_query.format(**kwargs)
                    data = self.ext_conn.query(sparql)
                else:
                    try:
                        data = get_all_item_data(
                                items=kwargs[kwargs['iri_key']],
                                conn=self.ext_conn,
                                output='json',
                                debug=False)
                        log.debug("data triple count: %s", len(data))
                    except KeyError:
                        raise KeyError("missing kwarg['iri_key'] defining which"
                                       " kwarg to use that contians the subject"
                                       " uri used to query for data. Example: "
                                       "iri_key='instance_iri, instance_iri="
                                       "<http://some.iri>")
                kwargs['dataset'] = RdfDataset(data)
                # pdb.set_trace()
        # start = datetime.datetime.now()
        super(SPARQLProcessor, self).run(**kwargs)
        # print("query time: ", (datetime.datetime.now() - start))
        self.output = kwargs['output']
        return kwargs['output']

    def execute(self, triple_map, output, **kwargs):
        """Execute """
        subjects = []
        if NS_MGR.ql.JSON.rdflib in \
                triple_map.logicalSource.reference_formulations:
            output_format = "json"
        else:
            output_format = "xml"
        if 'limit' not in kwargs:
            kwargs['limit'] = self.limit
        if 'offset' not in kwargs:
            kwargs['offset'] = self.offset
        # log.debug("triple_map.logicalSource: \n%s",
                  # pprint.pformat(triple_map.logicalSource.__dict__))
        iterator = str(triple_map.logicalSource.iterator)
        start = datetime.datetime.now()
        key, json_query = None, None
        # pdb.set_trace()
        if hasattr(triple_map.logicalSource, 'json_query') \
                and self.use_json_qry:
            key = kwargs.get(str(triple_map.logicalSource.json_key))
            if not key:
                key =[val for val in kwargs.values() \
                      if isinstance(val, rdflib.URIRef)][0]
            json_query = triple_map.logicalSource.json_query
            bindings = kwargs['dataset'].json_qry(json_query, {'$': key})
        else:
            sparql = PREFIX + triple_map.logicalSource.query.format(**kwargs)
            bindings = self.__get_bindings__(sparql, output_format)
        for binding in bindings:
            if key:
                try:
                    entity_raw = binding.subject.rdflib
                except AttributeError:
                    entity_raw = binding
            else:
                entity_raw = binding.get(iterator)
            if isinstance(entity_raw, (rdflib.URIRef,
                                       rdflib.BNode,
                                       BaseRdfDataType)):
                entity = entity_raw
            else:
                raw_value = entity_raw.get('value')
                if entity_raw.get('type').startswith('bnode'):
                    entity = BlankNode(raw_value)
                else:
                    entity = Uri(raw_value)
            if triple_map.subjectMap.class_ is not None:
                sub = entity
                if isinstance(entity, BaseRdfDataType):
                    sub = entity.rdflib
                output.add((sub,
                                 NS_MGR.rdf.type.rdflib,
                                 triple_map.subjectMap.class_))
            # pdb.set_trace()
            for pred_obj_map in triple_map.predicateObjectMap:
                predicate = pred_obj_map.predicate
                kwargs[iterator] = entity

                if pred_obj_map.parentTriplesMap is not None:
                    self.__handle_parents__(
                            output=output,
                            parent_map=pred_obj_map.parentTriplesMap,
                            subject=entity,
                            predicate=predicate,
                            **kwargs)
                    continue
                if pred_obj_map.reference is not None:
                    ref_key = str(pred_obj_map.reference)
                    if pred_obj_map.json_query:
                        # if pred_obj_map.json_query =="$.schema_logo":
                        # pdb.set_trace()
                        if ref_key in binding:
                            for item in binding[ref_key]:
                                output.add((entity,
                                                 predicate,
                                                 item.rdflib))
                            continue
                    else:
                        if ref_key in binding:
                            object_ = __get_object__(
                                binding[ref_key])
                            output.add((entity, predicate, object_))
                        continue
                if pred_obj_map.constant is not None:
                    if isinstance(entity, BaseRdfDataType):
                        entity = entity.rdflib
                    output.add(
                        (entity, predicate, pred_obj_map.constant))
                    continue

                json_query = None
                if pred_obj_map.json_query and self.use_json_qry:
                    json_query = pred_obj_map.json_query
                    start = datetime.datetime.now()
                    # pdb.set_trace()
                    # if str(pred_obj_map.predicate) == "http://purl.org/dc/terms/creator":
                    #     pdb.set_trace()
                    pre_obj_bindings = kwargs['dataset'].json_qry(json_query,
                                                                  {'$': entity})
                else:
                    sparql_query = PREFIX + pred_obj_map.query.format(**kwargs)
                    pre_obj_bindings = self.__get_bindings__(sparql_query,
                                                             output_format)

                for row in pre_obj_bindings:
                    if json_query and self.use_json_qry:
                        if isinstance(entity, BaseRdfDataType):
                            entity = entity.rdflib
                        output.add((entity, predicate, row.rdflib))
                    else:
                        object_ = __get_object__(row)
                        if object_ is None:
                            continue
                        if isinstance(entity, BaseRdfDataType):
                            entity = entity.rdflib
                        output.add((entity, predicate, object_))
            subjects.append(entity)
        return subjects

class SPARQLBatchProcessor(Processor):
    """Class batches all triple_maps queries into a single SPARQL query
    in an attempt to reduce the time spent in the triplestore/network
    bottleneck"""

    rdf_name = Uri("kdr:RmlSPARQLBatchProcessor")

    def __init__(self, rml_rules, triplestore_url=None, triplestore=None):
        super(SPARQLBatchProcessor, self).__init__(rml_rules, **kwargs)
        __set_prefix__()
        if triplestore_url is not None:
            self.triplestore_url = triplestore_url
        elif triplestore is not None:
            self.triplestore = triplestore

    def __get_bindings__(self, sparql):
        bindings = []
        if self.triplestore_url is not None:
            result = requests.post(
                self.triplestore_url,
                data={"query": sparql,
                      "format": "json"})
            bindings = result.json().get("results").get("bindings")
        elif self.triplestore is not None:
            result = self.triplestore.query(sparql)
            bindings = result.bindings

        return bindings

    def __construct_compound_query__(self, triple_map):
        select_clause = PREFIX + """
SELECT"""
        where_clause = """
WHERE {{"""

        for pred_map in triple_map.predicateObjectMap:
            if pred_map.constant is not None or\
               pred_map.reference is not None:
                continue
            #if pred_obj_map.parentTriplesMap is not None:
            #    self.__handle_parents__(
            #        parent_map=pred_obj_map.parentTriplesMap,
            #        subject=entity,
            #        predicate=predicate,
            #        **kwargs)
            #        continue
            select_line = pred_map.query.splitlines()[0]
            for term in select_line.split():
                if term.startswith("?") and term not in select_clause:
                    select_clause += " {}".format(term)
            where_clause += "\nOPTIONAL{{\n\t" +\
                        pred_map.query +\
                        "\n}}\n"
        return select_clause + where_clause + "}}"

    def run(self, **kwargs):
        kwargs['output'] = self.__graph__()
        super(SPARQLBatchProcessor, self).run(**kwargs)
        self.output = kwargs['output']
        return kwargs['output']

    def execute(self, triple_map, output, **kwargs):
        """Method iterates through triple map's predicate object maps
        and processes query.

        Args:
            triple_map(SimpleNamespace): Triple Map
        """
        sparql = PREFIX + triple_map.logicalSource.query.format(
            **kwargs)
        bindings = self.__get_bindings__(sparql)
        iterator = str(triple_map.logicalSource.iterator)
        for binding in bindings:
            entity_dict = binding.get(iterator)
            if isinstance(entity_dict, rdflib.term.Node):
                entity = entity_dict
            elif isinstance(entity_dict, dict):
                raw_value = entity_dict.get('value')
                if entity_dict.get('type').startswith('bnode'):
                    entity = rdflib.BNode(raw_value)
                else:
                    entity = rdflib.URIRef(raw_value)
            if triple_map.subjectMap.class_ is not None:
                output.add(
                    (entity,
                     rdflib.RDF.type,
                     triple_map.subjectMap.class_))

            sparql_query = self.__construct_compound_query__(
                triple_map).format(**kwargs)
            properties = self.__get_bindings__(sparql_query)
            for pred_obj_map in triple_map.predicateObjectMap:
                predicate = pred_obj_map.predicate
                if pred_obj_map.constant is not None:
                    output.add(
                        (entity, predicate, pred_obj_map.constant))
                    continue
                if "#" in str(predicate):
                    key = str(predicate).split("#")[-1]
                else:
                    key = str(predicate).split("/")[-1]

                for property_ in properties:
                    if key in property_.keys():
                        info = {"about": property_.get(key)}
                        object_ = __get_object__(info)
                        output.add((entity, predicate, object_))


def __set_prefix__():
    global PREFIX
    PREFIX = NS_MGR.prefix()
    return PREFIX

PREFIX = NS_MGR.prefix()

DEDUP_RULE = PREFIX + """
SELECT DISTINCT ?class ?bf_match
WHERE {
   ?map rr:subjectMap ?sub_map .
   ?sub_map rr:class ?class .
   ?sub_map kds:deduplicate ?bf_match
}"""


DEDUP_TRIPLESTORE = PREFIX + """
SELECT DISTINCT ?subj
WHERE {{
    ?subj rdf:type <{0}> .
    ?subj <{1}> ?name .
    FILTER(CONTAINS(?name, \"""{2}\"""))
}}"""


GET_TRIPLE_MAPS = PREFIX + """
SELECT DISTINCT ?map
WHERE {
    ?map rdf:type rr:TriplesMap .
}"""
