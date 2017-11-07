"""Flask Blueprint for core views"""
__author__ = "Mike Stabile, Jeremy Nelson"

import os
import inspect
import logging
import json
import requests
import cgi
import pdb
from flask import Flask, Blueprint, jsonify, render_template, \
                  Response, request
from flask_wtf import CsrfProtect, Form
from wtforms.fields import TextAreaField, StringField
from keanfunctions import EsBase, sample_data_map, sample_data_convert
from elasticsearch import Elasticsearch
    
MODULE_NAME = os.path.basename(inspect.stack()[0][1])

base_site = Blueprint("base_site", __name__,
                       template_folder="testing_templates")
base_site.config = {}

sample_data = sample_data_map()

def html_sample_data(path, data):
    odd = lambda i : 'even_row' if (i % 2 == 0) else 'odd_row'
    html = """
            <style>
                .even_row {
                    background: lightgoldenrodyellow; 
                }
                td {
                    padding: 0px 20px 0px 20px
                }
                tr:hover {
                    background: lightblue
                }
            </style>"""
    html +=  "<h3>%s</h3><table><tr><th>%s</th></tr>%s</table>" % \
            (path,
             "</th><th>".join(['Field','Mapping','Data']),
             "".join(["<tr class='%s'><td>%s</td></tr>" % \
                      (odd(i),
                       "</td><td>".join([cgi.escape(fld) for fld in field])) \
                      for i, field in enumerate(data)]))
    # print(html)
    return html

@base_site.route("/")
def api_instructions():
    

    warning = {"Routes": {
                    "/api/list/<es_index>/<doc_type>": get_lookup_list.__doc__}}
    html = """
    <h1>Kean Bibframe Catalog API</h1>
    <h2>Routes</h2>
    <h3>/api/search/[es_index]/[doc_type]</h3>
    {}
    <h3>/api/item/[es_index]/[doc_type]</h3>
    {}
    <h2>es_index and doc_type</h2>
    <p>catalog --> work</p>
    <p>reference --> topics</p>
    <h3>Sample Data for each index</h3>
    """.format(format_doc_html(get_lookup_list.__doc__),
               format_doc_html(get_lookup_item.__doc__))
    for path, data in sample_data.items():
        html += html_sample_data(path, data)
    return "<body style='font-family: monospace;'>%s</body>" % html

@base_site.route("/api/search/<es_index>/<doc_type>")
def get_lookup_list(es_index, doc_type, **kwargs):
    ''' Returns search results based on relevancy or an ordered list of 
    items.

    Request Params:
        term:       (optional)the search keywords
        size:       (default=10) the number of results to return
        from:       (optional) the starting point in the result set. Used for
                    pagination
        method:     (optional)['serach','list']
                        search: (default) will return results based on relevance
                        list: a 'fields' value must be supplied
        fields:     (optional) a CSV list of fields to return. returns the 
                    entire document if left blank 
        search_flds:(optional) a CSV list of fields to search. Higher relevancy 
                    is placed on these fields. defaults to fields paramater if 
                    left blank
        sort_dir:   (optional) the direction to sort the results. 
                    ['asc','desc','none']
        sort_flds:  (optional) a CSV list of fields for sorting the results.
                    defaults to 'fields' paramater if supplied
        filter_val: (optional) value to filter results on ***must supply a 
                    filter_fld value
        filter_fld: (optional) the field to fileter results on *** used in 
                    conjunction with 'filter_val'
        calc:       (optional) use '+' field_names and double quotes to add text
                    fld1 +", " + fld2 = "fld1, fld2" *** make sure the string is
                    encoded for a url i.e. '+' is %2B 
                    The calculated result will be in the '_calc' field

    Example Calls:
        General search on all fields:
            /api/search/[es_index]/[doc_type]?term=agriculture
        Give a higher result to documents with the search term in specific fields:
            /api/search/[es_index]/[doc_type]?term=agriculture&search_flds=rdfs_label,rdf_value
        Return only specific fields:
            /api/search/[es_index]/[doc_type]?term=agriculture&fields=label,value
        Return a calculated item:
            /api/search/[es_index]/[doc_type]?term=agriculture&calc=label+": "+value
        Return a list of docs filtered on a value:
            ...?method=list&fields=rdfs_label&filter_val=Cosmology&filter_fld=bf_subject.rdfs_label&sort=asc
    '''


    fields = param_list(kwargs.get("fields", request.args.get("fields")))
    search_flds = param_list(kwargs.get("search_flds",
                                        request.args.get("search_flds")))
    sort_dir = kwargs.get("", request.args.get("sort_dir"))
    sort_fields = param_list(kwargs.get("sort_fields", 
                             request.args.get("sort_fields")))
    raw = kwargs.get("raw", request.args.get("raw"))
    term = kwargs.get("term", request.args.get("term"))
    filter_field = kwargs.get("filter_fld", request.args.get("filter_fld"))
    filter_value = kwargs.get("filter_val", request.args.get("filter_val"))
    calc = kwargs.get("calc", request.args.get("calc"))
    method = kwargs.get("method", request.args.get("method","search"))
    size = kwargs.get("size", request.args.get("size",10))
    from_ = kwargs.get("from", request.args.get("from"))
    highlight = kwargs.get("highlight", request.args.get("highlight", False))
    search = EsBase(es_index=es_index)
    result = search.get_list(doc_type=doc_type,
                             fields=fields,
                             search_flds=search_flds,
                             sort_dir=sort_dir,
                             sort_fields=sort_fields,
                             method=method,
                             size=size,
                             term=term,
                             from_=from_,
                             filter_field=filter_field,
                             filter_value=filter_value,
                             highlight=highlight,
                             calc=calc)
    
    if request.full_path.startswith("/api/"):
        return jsonify(result)
    else:
        return result

@base_site.route("/api/item/<es_index>/<doc_type>")
@base_site.route("/api/item/<es_index>/<doc_type>/")
@base_site.route("/api/item/<es_index>/<doc_type>/<id>")
def get_lookup_item(es_index, doc_type, id=None, **kwargs):
    """ Returns a single item from the spedified index and doc_type
    
    Request Params:
        id: the id value associated with the id_field
        id_field: the field supplying the identifier | default: _id
        output: 'json'(default) or'sample' -> sample provides an html display
                of data with full field names.  

    Example Calls:
        Call for a document suppling only an 'id':
            /api/item/[es_index]/[doc_type]/lkajflk5342509daspjfal239
                    or
            /api/item/[es_index]/[doc_type]?id=lkajflk5342509daspjfal239

        Call for a document keying on a different field than the id:
            /api/item/[es_index]/[doc_type]?id=0958473827&id_field=bf_hasInstance.bf_identifiedBy.value
    
        Call for a document by 'id' returning with html sample:
            /api/item/[es_index]/[doc_type]/lkajflk5342509daspjfal239?output=sample
    """
    
    lg = logging.getLogger("%s:%s" % (MODULE_NAME, inspect.stack()[0][3]))
    lg.setLevel(logging.DEBUG)    
    output = kwargs.get("output", request.args.get("output", "json"))

    id_field = kwargs.get("id_field", request.args.get("id_field", "_id"))
    if id:
        item_id = id
    else:
        item_id = kwargs.get("id", request.args.get("id"))     

    search = EsBase(es_index=es_index, doc_type=doc_type)
    result = search.get_doc(id_field=id_field,
                            item_id=item_id)

    if request.full_path.startswith("/api/"):
        if output == 'sample':
            return html_sample_data("/".join([es_index, doc_type, id]), 
                    sample_data_convert(result, es_index, doc_type))
            
        return jsonify(result)
    else:
        return result
    
def param_list(param, split_term=","):
    """ Takes a paramater and converts to a list or returns none.

    args:
        param: the parmater to change into a list
        split_term: the value to split the parameter on.
        
    returns:
        None: if the param is None
        []: a list of terms
    """
    if param is None:
        return None
    elif isinstance(param, list):
        return param
    else:
        return param.split(split_term)


def format_doc_html(doc_string):
    lines = doc_string.split("\n")
    rtn_val = []
    for i, line in enumerate(lines):
        if i == 0:
            line = "   " + line
        if line.endswith(":"):
            line = "<h4>%s</h4>" % cgi.escape(line)
        elif ":" in line and line.find(":") < 60:
            parts = line.split(":")
            parts[0] = "<strong>%s</strong>" % cgi.escape(parts[0])
            line = ":".join([parts[0]] + [cgi.escape(part) for part in parts[1:]])
        elif line.strip().startswith("**"):
            line = "<h5>%s</h5>" % cgi.escape(line)
        line = "&nbsp".join(line.split(" "))
        if line.strip() != "":
            rtn_val.append(line)
    return "<br />".join(rtn_val)


class DslTester(Form):
    """ wtForm for the dsl tester form """
    index = StringField("Index")
    doc_type = StringField("Doc Type")
    dslbox = TextAreaField("DSL Query")

@base_site.route("/dsl", methods=['GET', 'POST'])
@base_site.route("/dsl/", methods=['GET', 'POST'])
@base_site.route("/dsl/index.html", methods=['GET', 'POST'])
def dsltester():
    ''' returns a list of videos in the database '''
    form = DslTester()
    dsl_results = {}
    es = Elasticsearch()
    if request.method == "POST":
        if form.index.data and form.dslbox.data:
            body=json.loads(form.dslbox.data)
            results = es.search(index=form.index.data,
                                body=body, 
                                doc_type= form.doc_type.data,
                                ignore=[400, 404])
            dsl_results = json.dumps(results, indent=4)
    return render_template("dsltester.html",
                           form=form,
                           dsl_results=dsl_results)