"""
Conversion functions for converting rdfclass and property instances to their
elasticsearch representation
"""
import pdb
from hashlib import sha1
from rdfframework.utilities import LABEL_FIELDS, VALUE_FIELDS
from rdfframework.datatypes import BaseRdfDataType, BlankNode, RdfNsManager

__author__ = "Mike Stabile, Jeremy Nelson"
__MODULE__ = __import__(__name__)

es_idx_types = {
    'es_Raw': {'keyword': {'type': 'keyword'}},
    'es_Lower': {'lower': {'type': 'text',
                           'analyzer': 'keylower'}},
    'es_NotAnalyzed': "keyword",
    'es_NotIndexed': False,
    'es_Ignored': False,
    'es_Standard': {}
}
NSM = RdfNsManager()

def convert_value_to_es(value, ranges, obj, method=None):
    """
    Takes an value and converts it to an elasticsearch representation

    args:
        value: the value to convert
        ranges: the list of ranges
        method: convertion method to use
                'None': default -> converts the value to its json value
                'missing_obj': adds attributes as if the value should have
                               been a rdfclass object
    """

    def sub_convert(val):
        """
        Returns the json value for a simple datatype or the subject uri if the
        value is a rdfclass

        args:
            val: the value to convert
        """
        if isinstance(val, BaseRdfDataType):
            return val.to_json
        elif isinstance(value, __MODULE__.rdfclass.RdfClassBase):
            return val.subject.sparql_uri
        return val

    if method == "missing_obj":
        rtn_obj = {
            "rdf_type": [rng.sparql_uri for rng in ranges], # pylint: disable=no-member
            "label": [getattr(obj, label)[0] \
                     for label in LABEL_FIELDS \
                     if hasattr(obj, label)][0]}
        try:
            rtn_obj['uri'] = value.sparql_uri
            rtn_obj["rdfs_label"] = NSM.nouri(value.sparql_uri)
        except AttributeError:
            rtn_obj['uri'] = "None Specified"
            rtn_obj['rdfs_label'] = sub_convert(value)
        rtn_obj['value'] = rtn_obj['rdfs_label']
        return rtn_obj
    return sub_convert(value)

def get_idx_types(rng_def, ranges):
    """
    Returns the elasticsearch index types for the obj

    args:
        rng_def: the range defintion dictionay
        ranges: rdfproperty ranges
    """
    idx_types = rng_def.get('kds_esIndexType', []).copy()
    if not idx_types:
        nested = False
        for rng in ranges:
            if range_is_obj(rng, __MODULE__.rdfclass):
                nested = True
        if nested:
            idx_types.append('es_Nested')
    return idx_types

def get_prop_range_defs(class_names, def_list):
    """
    Filters the range defitions based on the bound class

    args:
        obj: the rdffroperty instance
    """

    try:
        cls_options = set(class_names + ['kdr_AllClasses'])
        return [rng_def for rng_def in def_list \
                if not isinstance(rng_def, BlankNode) \
                and cls_options.difference(\
                        set(rng_def.get('kds_appliesToClass', []))) < \
                        cls_options]
    except AttributeError:
        return []

def get_prop_range_def(rng_defs):
    """
    Returns unique range defintion for current instance

    args:
        rng_defs: the output from 'get_prop_range_defs'
    """
    if len(rng_defs) > 1:
        pass
        #! write function to merge range defs
    try:
        return rng_defs[0]
    except IndexError:
        return {}

def range_is_obj(rng, rdfclass):
    """ Test to see if range for the class should be an object
    or a litteral
    """
    if rng == 'rdfs_Literal':
        return False
    if hasattr(rdfclass, rng):
        mod_class = getattr(rdfclass, rng)
        for item in mod_class.cls_defs['rdf_type']:
            try:
                if issubclass(getattr(rdfclass, item),
                              rdfclass.rdfs_Literal):
                    return False
            except AttributeError:
                pass
        if isinstance(mod_class, rdfclass.RdfClassMeta):
            return True
    return False

__IGN_KEYS__ = ['uri', 'id', 'value', 'label', 'rdf_type', 'kds_esIndexTime']
__COMBINED__ = VALUE_FIELDS + LABEL_FIELDS
__ALL_IGN__ = set(__COMBINED__ + __IGN_KEYS__)

def get_es_value(obj, def_obj):
    """
    Returns the value for an object that goes into the elacticsearch 'value'
    field

    args:
        obj: data object to update
        def_obj: the class instance that has defintion values
    """
    def get_dict_val(item):
        """
        Returns the string representation of the dict item
        """
        if isinstance(item, dict):
            return str(item.get('value'))
        return str(item)

    value_flds = []
    if def_obj.es_defs.get('kds_esValue'):
        value_flds = def_obj.es_defs['kds_esValue'].copy()
    else:
        # pdb.set_trace()
        value_flds = set(obj).difference(__ALL_IGN__)
        value_flds = list(value_flds)
    value_flds += __COMBINED__
    try:
        obj['value'] = [obj.get(label) for label in value_flds
                        if obj.get(label)][0]
    except IndexError:
        obj['value'] = ", ".join(["%s: %s" % (value.get('label'),
                                              value.get('value'))
                                  for prop, value in obj.items()
                                  if isinstance(value, dict) and \
                                  value.get('label')])

    if isinstance(obj['value'], list):
        obj['value'] = ", ".join([get_dict_val(item) for item in obj['value']])
    else:
        obj['value'] = get_dict_val(obj['value'])
    if str(obj['value']).strip().endswith("/"):
        obj['value'] = str(obj['value']).strip()[:-1].strip()
    if not obj['value']:
        obj['value'] = obj.get('uri', '')
    return obj

def get_es_label(obj, def_obj):
    """
    Returns object with label for an object that goes into the elacticsearch
    'label' field

    args:
        obj: data object to update
        def_obj: the class instance that has defintion values
    """
    label_flds = LABEL_FIELDS
    if def_obj.es_defs.get('kds_esLabel'):
        label_flds = def_obj.es_defs['kds_esLabel'] + LABEL_FIELDS
    try:
        for label in label_flds:
            if def_obj.cls_defs.get(label):
                 obj['label'] = def_obj.cls_defs[label][0]
                 break
        if not obj.get('label'):
            obj['label'] = def_obj.__class__.__name__.split("_")[-1]
    except AttributeError:
        # an attribute error is caused when the class is only
        # an instance of the BaseRdfClass. We will search the rdf_type
        # property and construct a label from rdf_type value
        if def_obj.get('rdf_type'):
            obj['label'] = def_obj['rdf_type'][-1].value[-1]
        else:
            obj['label'] = "no_label"
    return obj

def get_es_ids(obj, def_obj):
    """
    Returns the object updated with the 'id' and 'uri' fields for the
    elasticsearch document

    args:
        obj: data object to update
        def_obj: the class instance that has defintion values
    """
    try:
        path = ""
        for base in [def_obj.__class__] + list(def_obj.__class__.__bases__):

            if hasattr(base, 'es_defs') and base.es_defs:
                path = "%s/%s/" % (base.es_defs['kds_esIndex'][0],
                                   base.es_defs['kds_esDocType'][0])
                continue
    except KeyError:
        path = ""
    if def_obj.subject.type == 'uri':
        obj['uri'] = def_obj.subject.clean_uri
        obj['id'] = path + make_es_id(obj['uri'])
    elif def_obj.subject.type == 'bnode':
        obj['id'] = path + def_obj.bnode_id()
    else:
        obj['id'] = path + make_es_id(str(obj['value']))
    return obj

def make_es_id(uri):
    """
    Creates the id based off of the uri value

    Args:
    -----
        uri: the uri to conver to an elasticsearch id
    """
    try:
        uri = uri.clean_uri
    except AttributeError:
        pass
    return sha1(uri.encode()).hexdigest()
