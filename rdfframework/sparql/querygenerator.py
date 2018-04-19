import os
import requests
import copy
import json
import pdb


from rdfframework.utilities import render_without_request, UniqueList
from rdfframework.datatypes import RdfNsManager, Uri

NSM = RdfNsManager()
DEBUG = True

def run_query_series(queries, conn):
    """
    Iterates through a list of queries and runs them through the connection

    Args:
    -----
        queries: list of strings or tuples containing (query_string, kwargs)
        conn: the triplestore connection to use
    """
    results = []
    for item in queries:
        qry = item
        kwargs = {}
        if isinstance(item, tuple):
            qry = item[0]
            kwargs = item[1]
        result = conn.update_query(qry, **kwargs)
        # pdb.set_trace()
        results.append(result)
    return results

def get_all_item_data(items, conn, graph=None, output='json', **kwargs):
    """ queries a triplestore with the provided template or uses a generic
    template that returns triples 3 edges out in either direction from the
    provided item_uri

    args:
        items: the starting uri or list of uris to the query
        conn: the rdfframework triplestore connection to query against
        output: 'json' or 'rdf'

    kwargs:
        template: template to use in place of the generic template
        rdfclass: rdfclass the items are based on.
        filters: list of filters to apply
    """
    # set the jinja2 template to use
    if kwargs.get('template'):
        template = kwargs.pop('template')
    else:
        template = "sparqlAllItemDataTemplate.rq"
    # build the keyword arguments for the templace
    template_kwargs = {"prefix": NSM.prefix(), "output": output}
    if isinstance(items, list):
        template_kwargs['uri_list'] = items
    else:
        template_kwargs['item_uri'] = Uri(items).sparql
    if kwargs.get("special_union"):
        template_kwargs['special_union'] = kwargs.get("special_union")
    if kwargs.get('rdfclass'):
        # pdb.set_trace()
        template_kwargs.update(kwargs['rdfclass'].query_kwargs)
    if kwargs.get("filters"):
        template_kwargs['filters'] = make_sparql_filter(kwargs.get('filters'))
    sparql = render_without_request(template, **template_kwargs)
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

def add_sparql_line_nums(sparql):
    """
    Returns a sparql query with line numbers prepended
    """
    lines = sparql.split("\n")
    return "\n".join(["%s %s" % (i + 1, line) for i, line in enumerate(lines)])
