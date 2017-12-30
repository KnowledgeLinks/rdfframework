import os
import requests
import copy
import json
import pdb


from rdfframework.utilities import render_without_request, UniqueList
from rdfframework.datatypes import RdfNsManager, Uri

NSM = RdfNsManager()
DEBUG = True

def get_all_item_data(item_uri, conn, graph=None, output='json', **kwargs):
    """ queries a triplestore with the provided template or uses a generic
    template that returns triples 3 edges out in either direction from the
    provided item_uri

    args:
        item_uri: the starting uri of the query
        conn: the rdfframework triplestore connection to query against
        output: 'json' or 'rdf'

    kwargs:
        template: template to use in place of the generic template
    """
    if kwargs.get('template'):
        template = kwargs.pop('template')
    else:
        template = "sparqlAllItemDataTemplate.rq"
    # kwargs['filters'] = filters
    filter_str = make_sparql_filter(kwargs.get('filters'))
    sparql = render_without_request(template,
                                    prefix=NSM.prefix(),
                                    item_uri=Uri(item_uri).sparql,
                                    output=output,
                                    filters=filter_str)
    return conn.query(sparql, **kwargs)

def get_graph(graph, conn, **kwargs):
    """ Returns all the triples for a specific are graph

    args:
        graph: the URI of the graph to retreive
        conn: the rdfframework triplestore connection
    """
    sparql = render_without_request("sparqlGraphDataTemplate.rq",
                                    prefix=NSM.prefix(),
                                    graph=graph)
    return conn.query(sparql, **kwargs)

def make_sparql_filter(filters):
    """ Make the filter section for a query template

    args:
        filters: list of dictionaries to generate the filter

    example:
        filters = [{'variable': 'p',
                    'operator': '=',
                    'union_type': '||',
                    'values': ['rdf:type', 'rdfs:label']}]
    """
    def make_filter_str(variable, operator, union_type, values):
        """ generates a filter string for a sparql query

        args:
            variable: the variable to reference
            operator: '=' or '!='
            union_type" '&&' or '||'
            values: list of values to apply the filter
        """
        formated_vals = UniqueList()
        for val in values:
            try:
                formated_vals.append(val.sparql)
            except AttributeError:
                formated_vals.append(val)
        pre_str = "?%s%s" % (variable.replace("?", ""), operator)
        union = "%s\n\t\t" % union_type
        return "\tFilter( %s) .\n" % union.join([pre_str + val
                                                      for val in formated_vals])

    if not filters:
        return ""
    rtn_str = ""
    for param in filters:
        rtn_str += make_filter_str(**param)
    return rtn_str
