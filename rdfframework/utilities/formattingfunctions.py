import pdb

from .baseutilities import make_list
from .rdfvocabcorrelations import *


def string_wrap(string, width=80, indent=0, subindent='auto'):
    rtn_list = []
    line_list = []
    string = " ".join(string.replace("\n","").split())
    words = string.split(" ")
    line_len = indent
    if indent > 0:
        line_list.append(" "*(indent-1))
    # determine the subindent number
    if subindent == 'auto':
        subindent = len(words[0]) + 1
    else:
        try:
            int(subindent)
        except ValueError:
            subindent = 1
    # generate the lines
    for word in words:
        # see if adding the next word makes the line longer than the width
        if line_len + len(word) < width and len(word) < width:
            line_list.append(word)
            line_len += len(word) + 1
        # if the word by itsself is greater than the width add it anyway
        elif len(word) >= width:
            rtn_list.append(word)
        # start a new line
        else:
            rtn_list.append(" ".join(line_list))
            line_list = []
            if indent > 0:
                line_list.append(" "*(indent + subindent - 1))
            line_list.append(word)
            line_len = indent + len(word) + 1 + subindent
    rtn_list.append(" ".join(line_list))
    return "\n".join(rtn_list)

def find_values(field_list, data, seperator = " -- ", method='dict'):
    if method == 'dict':
        new_list = [(key, data.get(key)) for key in field_list if data.get(key)]
    elif method == 'class':
        new_list = [(key, getattr(data, key))
                    for key in field_list
                    if hasattr(data, key)]
    rtn_list = []
    # if the values do not need to to concatenated return the new_list
    if seperator is None:
        return new_list
    # if items need to be concatenated merge them with the seperator value
    for item in new_list:
        if isinstance(item[1], list):
            item = (item[0], seperator.join(item[1]),)
        rtn_list.append(item)
    return rtn_list

def format_doc_vals(data,
                    descriptor,
                    seperator=": ",
                    divider=" | ",
                    subdivider=", ",
                    max_width=70,
                    indent=4,
                    subindent='auto',
                    key_join = False):
    line_data = []
    if descriptor:
        line_data.append("%s%s%s" %(" "*indent, descriptor, seperator))
    try:
        if key_join:
            rtn_val = "%s%s\n" % (descriptor, seperator)
        else:
            rtn_val = "%s%s%s" % (descriptor, seperator, data.pop(0)[1])
        if len(data) > 0 :
            if key_join:
                rtn_val = "%s%s%s" % (rtn_val, divider,
                        subdivider.join([string_wrap("%s: %s" % item, max_width,indent,subindent) for item in data]))
            else:
                rtn_val = "%s%s%s" % (rtn_val, divider,
                        subdivider.join([item[1] for item in data]))
                rtn_val = string_wrap(rtn_val, max_width, indent)
    except IndexError:
        rtn_val =""
    return rtn_val

def make_doc_string(name, cls_def, bases=[], props={}):
    from rdfframework.datatypes import RdfNsManager
    NSM = RdfNsManager()
    footer_text = """*** autogenerated from knowledgelinks.io rdfframework
                        rdf definitions"""
    doc_items = [name]
    label_fields = LABEL_FIELDS
    description_fields = DESCRIPTION_FIELDS
    note_fields = NOTE_FIELDS
    prop_fields = PROP_FIELDS
    label = format_doc_vals(data=find_values(label_fields, cls_def),
                            descriptor="Label",
                            divider=" | ",
                            subdivider=", ")
    if len(label) > 0:
        doc_items.append(label)
    description = format_doc_vals(data=find_values(description_fields, cls_def),
                                  descriptor="Description",
                                  divider="",
                                  subdivider="\n")
    if len(description) > 0:
        doc_items.append(description)
    parents = [("", NSM.ttluri(base.__name__)) for base in bases[:-1] if
               base.__name__ not in ['RdfPropertyBase', 'RdfClassBase']]
    if len(parents) > 0:
        cls_hierarchy = format_doc_vals(data=parents,
                                        descriptor="Class Hierarchy",
                                        divider=" -> ",
                                        subdivider=" -> ")
        doc_items.append(cls_hierarchy)

    for base in bases[:-1]:
        try:
            if "Properties:" in base.__doc__:
                doc_items.append(\
                        base.__doc__[ \
                        base.__doc__.find(\
                        "Properties"):].replace(\
                        "Properties:", "Inherited from %s:" \
                                % base.__name__).replace(footer_text,""))
        except TypeError:
            pass

    try:
        prop_notes = [(prop, " ".join([item[1] for item in \
                      find_values(description_fields,
                                  prop_def,
                                  method='dict')])) \
                      for prop, prop_def in props.items() \
                      if len(find_values(description_fields,
                                         prop_def,
                                         method='dict')) > 0]

        prop_notes.sort()
        properties = format_doc_vals(data=prop_notes,
                                      descriptor="Properties",
                                      divider="",
                                      subdivider="\n",
                                      subindent=14,
                                      key_join=True)

        doc_items.append(properties)
    except AttributeError:
        pass



    footer = format_doc_vals(data=[("",footer_text)],
                             descriptor="",
                             seperator="\n",
                             divider="\n",
                             subdivider="")
    doc_items.append(footer)
    return "\n\n".join(doc_items)

