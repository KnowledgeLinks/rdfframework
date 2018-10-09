import inspect
import functools
import pdb
import rdflib
import json

from decimal import Decimal
from rdfframework.utilities import cbool, new_id, memorize, \
        RegPerformInstanceMeta
from dateutil.parser import parse
from datetime import date, datetime, time, timezone
from .namespaces import Uri, BaseRdfDataType, PERFORMANCE_ATTRS

__author__ = "Mike Stabile, Jeremy Nelson"

class BlankNode(BaseRdfDataType, metaclass=RegPerformInstanceMeta):
    """ blankNode URI/IRI class for working with RDF data """
    class_type = "BlankNode"
    type = "bnode"
    es_type = "text"
    performance_mode = True
    performance_attrs = PERFORMANCE_ATTRS

    def __init__(self, value=None):
        if value:
            if not value.startswith("_:"):
                self.value = "_:" + value
            else:
                self.value = value
        else:
            self.value = "_:" + new_id()
        if self.performance_mode:
            for attr in self.performance_attrs:
                setattr(self, attr, self.value)
        self.hash_val = hash(self.value)

    def __hash__(self):
        return self.hash_val

    def __repr__(self):
        return  self.value

    def __str__(self):
        return self.value[2:]

    def __eq__(self, other):
        try:
            return self.value == other.value
        except AttributeError:
            try:
                return self.value == other.subject.value
            except AttributeError:
                return self.value == other

    @property
    def rdflib(self):
        """ Returns the rdflibURI reference """
        return rdflib.BNode(self.value[2:])

class XsdString(str, BaseRdfDataType):
    """ String instance of rdf xsd:string type value"""

    datatype = Uri("xsd:string")
    class_type = "XsdString"
    py_type = str
    es_type = "text"

    __slots__ = []

    def __new__(cls, *args, **kwargs):
        if isinstance(args[0], dict):
            new_args = (args[0].pop('value'), )
            kwargs.update(args[0])
        else:
            new_args = args
        if "xml:lang" in kwargs:
            lang = kwargs.pop("xml:lang")
        elif "lang" in kwargs:
            lang = kwargs.pop("lang")
        else:
            lang = None
        newobj = str.__new__(cls, *new_args)
        newobj.lang = lang
        newobj.value = str(new_args[0])
        return newobj

    def __init__(self, *args, **kwargs):
        pass

    def __repr__(self):
        return self._format(method="sparql")

    def __add__(self, other):
        if hasattr(other, "datatype"):
            rtn_lang = None
            if other.datatype == "xsd:string":
                rtn_val = self.value + other.value
                if other.lang and self.lang and other.lang != self.lang:
                    rtn_lang = None
                elif other.lang:
                    rtn_lang = other.lang
                else:
                    rtn_lang = self.lang
            else:
                rtn_val = self.value + str(other.value)
        else:
            rtn_val = self.value + str(other)
            rtn_lang = self.lang
        return XsdString(rtn_val, lang=rtn_lang)

    @property
    def rdflib(self):
        if self.lang:
            return rdflib.Literal(self.value, lang=self.lang)
        return rdflib.Literal(self.value, datatype=self.datatype.rdflib)

class RdfXMLLiteral(XsdString):
    datatype = Uri("rdf:XMLLiteral")
    class_type = "RdfXMLLiteral"
    py_type = None
    es_type = "text"

class XsdBoolean(BaseRdfDataType):
    """ Boolean instance of rdf xsd:boolean type value"""

    datatype = Uri("xsd:boolean")
    class_type = "XsdBoolean"
    py_type = bool
    es_type = "boolean"

    def __init__(self, value):
        new_val = cbool(value)
        if new_val is None:
            raise TypeError("'%s' is not a boolean value" % value)
        self.value = new_val

    def __eq__(self, value):
        if value == self.value:
            return True
        return False

    def __bool__(self):
        #pdb.set_trace()
        if self.value is None:
            return False
        return self.value

    def __hash__(self):
        return self.value

    @property
    def to_json(self):
        return json.dumps(self.value)

class XsdDate(date, BaseRdfDataType):
    """ Datetime Date instacne of rdf xsd:date type value"""

    datatype = Uri("xsd:date")
    class_type = "XsdDate"
    py_type = date
    es_type = "date"
    es_format = "strict_date_optional_time||epoch_millis"

    def __new__(cls, *args, **kwargs):
        yy = args[0]
        mm = args[1:2][0] if args[1:2] else 0
        dd = args[2:3][0] if args[2:3] else 0
        if isinstance(args[0], str):
            yy = parse(args[0])
        if isinstance(yy, date) or isinstance(yy, datetime):
            dd = yy.day
            mm = yy.month
            yy = yy.year
        try:
            return date.__new__(cls, yy, mm, dd, **kwargs)
        except:
            vals = tuple([1900, 1, 1])
            return date.__new__(cls, *vals)

    def __init__(self, *args, **kwargs):
        self.value = self

class XsdDatetime(datetime, BaseRdfDataType):
    """ Datetime Datetime instance of rdf xsd:datetime type value"""

    datatype = Uri("xsd:dateTime")
    class_type = "XsdDatetime"
    py_type = datetime
    es_type = "date"
    es_format = "strict_date_optional_time||epoch_millis"

    def __new__(cls, *args, **kwargs):
        # print("args: ", args)
        yy = args[0]
        mm = args[1:2][0] if args[1:2] else 0
        dd = args[2:3][0] if args[2:3] else 0
        hh = args[3:4][0] if args[3:4] else 0
        mi = args[4:5][0] if args[4:5] else 0
        ss = args[5:6][0] if args[5:6] else 0
        ms = args[6:7][0] if args[6:7] else 0
        tz = args[7:8][0] if args[7:8] else timezone.utc
        if isinstance(args[0], str):
            yy = parse(args[0])
        if isinstance(yy, datetime):
            tz = yy.tzinfo if yy.tzinfo else timezone.utc
            ms = yy.microsecond
            ss = yy.second
            mi = yy.minute
        if isinstance(yy, date) or isinstance(yy, datetime):
            hh = yy.hour
            dd = yy.day
            mm = yy.month
            yy = yy.year
        vals = tuple([yy, mm, dd, hh, mi, ss, ms, tz])
        try:
            return datetime.__new__(cls, *vals, **kwargs)
        except:
            vals = tuple([1900, 1, 1, 0, 0, 0, 0])
            return datetime.__new__(cls, *vals)

    def __init__(self, *args, **kwargs):
        self.value = self

    def __str__(self):
        # return str(self.value)
        return self.sparql

class XsdTime(time, BaseRdfDataType):
    """ Datetime Datetime instance of rdf xsd:datetime type value"""

    datatype = Uri("xsd:time")
    class_type = "XsdTime"
    py_type = time

    def __new__(cls, *args, **kwargs):
        hh = args[0]
        mi = args[1:2][0] if args[1:2] else 0
        ss = args[2:3][0] if args[2:3] else 0
        ms = args[3:4][0] if args[3:4] else 0
        tz = args[4:5][0] if args[4:5] else timezone.utc
        if isinstance(args[0], str):
            hh = parse(args[0])
        if isinstance(hh, datetime) or isinstance(hh, time):
            tz = hh.tzinfo if hh.tzinfo else timezone.utc
            ms = hh.microsecond
            ss = hh.second
            mi = hh.minute
            hh = hh.hour
        vals = tuple([hh, mi, ss, ms, tz])
        return time.__new__(cls, *vals, **kwargs)

    def __init__(self, *args, **kwargs):
        self.value = self

class XsdInteger(int, BaseRdfDataType):
    """ Integer instance of rdf xsd:string type value"""

    datatype = Uri("xsd:integer")
    class_type = "XsdInteger"
    py_type = int
    es_type = "long"

    def __new__(cls, *args, **kwargs):
        newobj = int.__new__(cls, *args, **kwargs)
        return newobj

    def __init__(self, *args, **kwargs):
        self.value = int(self)

    def __repr__(self):
        return self._format(method="sparql")

    def _internal_add(self, other):
        """ Used for specifing addition methods for
           __add__, __iadd__, __radd__
        """
        if hasattr(other, "datatype"):
            if other.datatype == self.datatype:
                rtn_val = self.value + other.value
            else:
                rtn_val = self.value + int(other.value)
        else:
            rtn_val = self.value + other
        return XsdInteger(rtn_val)

    def _internal_sub(self, other, method=None):
        """ Used for specifing addition methods for
           __add__, __iadd__, __radd__
        """
        if hasattr(other, "datatype"):
            if other.datatype == self.datatype:
                oval = other.value
            else:
                oval = int(other.value)
        else:
            oval = int(other)
        if method == 'rsub':
            rtn_val = oval - self.value
        else:
            rtn_val = self.value - oval
        return XsdInteger(rtn_val)

    def __add__(self, other):
        return self._internal_add(other)

    def __iadd__(self, other):
        return self._internal_add(other)

    def __radd__(self, other):
        return self._internal_add(other)

    def __sub__(self, other):
        return self._internal_sub(other)

    def __isub__(self, other):
        return self._internal_sub(other)

    def __rsub__(self, other):
        return self._internal_sub(other, 'rsub')

class XsdDecimal(Decimal, BaseRdfDataType):
    """ Integer instance of rdf xsd:string type value"""

    datatype = Uri("xsd:decimal")
    class_type = "XsdDecimal"
    py_type = Decimal
    es_type = "long"

    def __new__(cls, *args, **kwargs):
        vals = list(args)
        vals[0] = str(args[0])
        vals = tuple(vals)
        newobj = Decimal.__new__(cls, *vals, **kwargs)
        return newobj

    def __init__(self, *args, **kwargs):
        self.value = Decimal(str(self))

    def __repr__(self):
        return self._format(method="sparql")

    def _internal_add(self, other):
        """ Used for specifing addition methods for
           __add__, __iadd__, __radd__
        """
        if hasattr(other, "datatype"):
            if other.datatype == "xsd:decimal":
                rtn_val = self.value + Decimal(str(other.value))
            else:
                rtn_val = self.value + Decimal(str(other.value))
        else:
            rtn_val = self.value + Decimal(str(other))
        return XsdDecimal(str(float(rtn_val)))

    def _internal_sub(self, other):
        """ Used for specifing subtraction methods for
           __sub__, __isub__, __rsub__
        """
        if hasattr(other, "datatype"):
            if other.datatype == "xsd:decimal":
                rtn_val = self.value - Decimal(str(other.value))
            else:
                rtn_val = self.value - Decimal(str(other.value))
        else:
            rtn_val = self.value - Decimal(str(other))
        return XsdDecimal(str(float(rtn_val)))

    def __add__(self, other):
        return self._internal_add(other)

    def __iadd__(self, other):
        return self._internal_add(other)

    def __radd__(self, other):
        return self._internal_add(other)

    def __sub__(self, other):
        return self._internal_sub(other)

    def __isub__(self, other):
        return self._internal_sub(other)

    def __rsub__(self, other):
        return self._internal_sub(other)




__DT_LOOKUP__ = BaseRdfDataType.__registry__
# DT_LOOKUP = {}
# xsd_class_list = [Uri,
#                   BlankNode,
#                   XsdBoolean,
#                   XsdDate,
#                   XsdDatetime,
#                   XsdString,
#                   XsdTime,
#                   XsdInteger]
# for xsd_class in xsd_class_list:
#     attr_list = ["type", "py_type", "class_type"]
#     for attr in attr_list:
#         if hasattr(xsd_class, attr):
#             DT_LOOKUP[getattr(xsd_class, attr)] = xsd_class
#         elif hasattr(xsd_class, '__wrapped__') and \
#                 hasattr(xsd_class.__wrapped__, attr):
#             DT_LOOKUP[getattr(xsd_class.__wrapped__, attr)] = xsd_class
#     if hasattr(xsd_class, "datatype"):
#         DT_LOOKUP[xsd_class.datatype.sparql] = xsd_class
#         DT_LOOKUP[xsd_class.datatype.sparql_uri] = xsd_class
#         DT_LOOKUP[xsd_class.datatype.pyuri] = xsd_class
#         DT_LOOKUP[xsd_class.datatype.clean_uri] = xsd_class
#         DT_LOOKUP[xsd_class.datatype] = xsd_class
#     DT_LOOKUP[xsd_class] = xsd_class

# @memorize
def pyrdf2(value, class_type=None, datatype=None, lang=None, **kwargs):
    """ Coverts an input to one of the rdfdatatypes classes

        Args:
            value: any rdfdatatype, json dict or vlaue
            class_type: "literal", "uri" or "blanknode"
            datatype: "xsd:string", "xsd:int" , etc
    """
    try:

        if isinstance(value, dict):
            # test to see if the type is a literal, a literal will have a another
            # dictionary key call datatype. Feed the datatype to the lookup to
            # return the value else convert it to a XsdString
            if value.get('type') == "literal":
                if not value.get("datatype"):
                    return XsdString(value['value'])
                else:
                    try:
                        if value.get("lang"):
                            # The lang keyword only applies to XsdString types
                            return DT_LOOKUP[value['datatype']](value['value'],
                                    lang=value.get("lang"))
                        else:
                            return DT_LOOKUP[value['datatype']](value['value'])
                    except:
                        rtn_val = BaseRdfDataType(value['value'])
                        rtn_val.datatype = Uri(value['datatype'])
                        return rtn_val
            else:
                return DT_LOOKUP[value['type']](value['value'])
        elif isinstance(value, BaseRdfDataType):
            return value
        else:
            return DT_LOOKUP[type(value)](value)
    except:
        pdb.set_trace()
        pass
# TYPE_MATCH is a reference dict that is used with 'pyrdf' to for matching
# items in the the BaseRdfDataType registry for nested items. 'uri' and 'bnode'
# are single item dictionaries that reguire a matching key to lookup
__TYPE_MATCH__ = {"bnode": 'BlankNode',
                  "uri": 'Uri',
                  # if the literal value does not have a datatype use
                  # 'xsd_string' as the default
                  "literal": 'xsd_string'}

# @memorize
def pyrdf(value, class_type=None, datatype=None, **kwargs):
    """ Coverts an input to one of the rdfdatatypes classes

        Args:
            value: any rdfdatatype, json dict or vlaue
            class_type: "literal", "uri" or "blanknode"
            datatype: "xsd:string", "xsd:int" , etc
        kwargs:
            lang: language tag
    """
    if isinstance(value, BaseRdfDataType):
        return value
    if isinstance(value, dict):
        value = value.copy()
        class_type = value.pop('type')
        try:
            datatype = value.pop('datatype')
        except KeyError:
            datatype = __TYPE_MATCH__[class_type]
        kwargs = value
        value = kwargs.pop('value')
    if not class_type:
        class_type = 'literal'
    if not datatype:
        datatype = type(value)
    try:
        # print("pyrdf: ", value, " class_type: ", class_type, " datatype: ", datatype)
        return __DT_LOOKUP__[class_type][datatype](value, **kwargs)
    except KeyError:
        rtn_val = BaseRdfDataType(value)
        rtn_val.datatype = Uri(datatype)
        return rtn_val

"""
#! To be implemented

"xsd_anyURI":
        # URI (Uniform Resource Identifier)
"xsd_base64Binary":
        # Binary content coded as "base64"
"xsd_byte":
        # Signed value of 8 bits
"xsd_decimal":
        # Decimal numbers
"xsd_double":
        # IEEE 64
"xsd_duration":
        # Time durations
"xsd_ENTITIES":
        # Whitespace
"xsd_ENTITY":
        # Reference to an unparsed entity
"xsd_float":
        # IEEE 32
"xsd_gDay":
        # Recurring period of time: monthly day
"xsd_gMonth":
        # Recurring period of time: yearly month
"xsd_gMonthDay":
        # Recurring period of time: yearly day
"xsd_gYear":
        # Period of one year
"xsd_gYearMonth":
        # Period of one month
"xsd_hexBinary":
        # Binary contents coded in hexadecimal
"xsd_ID":
        # Definition of unique identifiers
"xsd_IDREF":
        # Definition of references to unique identifiers
"xsd_IDREFS":
        # Definition of lists of references to unique identifiers
"xsd_int":
        # 32
"xsd_integer":
        # Signed integers of arbitrary length
"xsd_language":
        # RFC 1766 language codes
"xsd_long":
        # 64
"xsd_Name":
        # XML 1.O name
"xsd_NCName":
        # Unqualified names
"xsd_negativeInteger":
        # Strictly negative integers of arbitrary length
"xsd_NMTOKEN":
        # XML 1.0 name token (NMTOKEN)
"xsd_NMTOKENS":
        # List of XML 1.0 name tokens (NMTOKEN)
"xsd_nonNegativeInteger":
        # Integers of arbitrary length positive or equal to zero
"xsd_nonPositiveInteger":
        # Integers of arbitrary length negative or equal to zero
"xsd_normalizedString":
        # Whitespace
"xsd_NOTATION":
        # Emulation of the XML 1.0 feature
"xsd_positiveInteger":
        # Strictly positive integers of arbitrary length
"xsd_QName":
        # Namespaces in XML
"xsd_short":
        # 32
"xsd_string":
        # Any string
"xsd_time":
        # Point in time recurring each day
"xsd_token":
        # Whitespace
"xsd_unsignedByte":
        # Unsigned value of 8 bits
"xsd_unsignedInt":
        # Unsigned integer of 32 bits
"xsd_unsignedLong":
        # Unsigned integer of 64 bits
"xsd_unsignedShort":
        # Unsigned integer of 16 bits
"""


