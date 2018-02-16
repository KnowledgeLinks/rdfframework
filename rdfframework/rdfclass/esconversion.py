"""
Conversion functions for converting rdfclass and property instances to their
elasticsearch representation
"""
import pdb
from hashlib import sha1
from rdfframework.utilities import LABEL_FIELDS, VALUE_FIELDS
from rdfframework.datatypes import BaseRdfDataType

__author__ = "Mike Stabile, Jeremy Nelson"
__MODULE__ = __import__(__name__)


def convert_value_to_es(value, method=None):
    """
    Takes an value and converts it to an elasticsearch representation

    args:
        value: the value to convert
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
            "rdf_type": [rng.sparql_uri for rng in self.rdfs_range], # pylint: disable=no-member
            "label": [getattr(self, label)[0] \
                     for label in LABEL_FIELDS \
                     if hasattr(self, label)][0]}
        try:
            rtn_obj['uri'] = value.sparql_uri
            rtn_obj["rdfs_label"] = NSM.nouri(value.sparql_uri)
        except AttributeError:
            rtn_obj['uri'] = "None Specified"
            rtn_obj['rdfs_label'] = sub_convert(value)
        rtn_obj['value'] = rtn_obj['rdfs_label']
        return rtn_obj
    return sub_convert(value)

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

__IGN_KEYS__ = ['uri', 'id', 'value', 'label', 'rdf_type']
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
            return item.get('value')
        return item

    value_flds = []
    if def_obj.es_defs.get('kds_esValue'):
        value_fls = def_obj.es_defs['kds_esValue']
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
    obj['value'] = get_dict_val(obj['value'])
    if isinstance(obj['value'], list):
        obj['value'] = ", ".join([get_dict_val(item) for item in obj['value']])
    if obj['value'].strip().endswith("/"):
        obj['value'] = obj['value'].strip()[:-1].strip()
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
        # an attribute error is caused when the class is an only
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
    elsaticsearch document

    args:
        obj: data object to update
        def_obj: the class instance that has defintion values
    """
    if def_obj.subject.type == 'uri':
        obj['uri'] = def_obj.subject.sparql_uri
        try:
            path = ""
            for base in [def_obj.__class__] + list(def_obj.__class__.__bases__):

                if hasattr(base, 'es_defs') and base.es_defs:
                    path = "%s/%s/" % (base.es_defs['kds_esIndex'][0],
                                       base.es_defs['kds_esDocType'][0])
                    continue
        except KeyError:
            path = ""
        obj['id'] = path + sha1(obj['uri'].encode()).hexdigest()
    return obj
