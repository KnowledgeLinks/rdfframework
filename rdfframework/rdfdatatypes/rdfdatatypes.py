import json
import pdb

from decimal import Decimal
from rdfframework.utilities import RdfNsManager as nsm, cbool, is_not_null, \
                                   DictClass, new_id
from dateutil.parser import parse
from datetime import date, datetime, time, timezone

NSM = nsm()
class BaseRdfDataType(object):
    """ Base for all rdf datatypes. Not designed to be used alone """
    type = "literal"
    default_method = "sparql"
    py_type = None

    def __init__(self, value):
        self.value = value

    def _format(self, method="sparql", dt_format="turtle"):
        """ formats the value """

        try:
            rtn_val = json.dumps(str(self.value))
        except:
            rtn_val = str(self.value)
        if method == "sparql":
            if self.type == 'literal':
                if hasattr(self, "datatype"):
                    if hasattr(self, "lang") and self.lang:
                        rtn_val += "@%s" % self.lang
                    else:
                        dt = self.datatype
                        if dt_format == "uri":
                            dt = NSM.uri(self.datatype)
                        if method == "sparql":
                            rtn_val += "^^%s" % dt
                else:
                    rtn_val += "^^xsd:string"
            elif self.type == 'uri':
                if dt_format == "turtle":
                    rtn_val = NSM.ttluri(self.value)
                else:
                    rtn_val = NSM.iri(NSM.uri(self.value))
            elif self.type == 'bnode':
                rtn_val = self.value
        elif method == "pyuri":
            rtn_val = NSM.pyuri(self.value)
        return rtn_val

    def __repr__(self):
        return self._format(method=self.default_method)

    @property
    def sparql(self):
        return self._format(method="sparql")

    @property
    def sparql_uri(self):
        return self._format(method="sparql", dt_format="uri")

    @property
    def debug(self):
        return DictClass(self)

class Uri(BaseRdfDataType):
    """ URI/IRI class for working with RDF data """
    class_type = "Uri"
    type = "uri"
    default_method = "pyuri"
    

    # def __new__(self, value):
    #     pdb.set_trace()
    #     if hasattr(value, "type") and value.type =="uri":
    #         return value
    #     else:
    #         return  self #return str.__new__(cls, *args, **kwargs)

    def __init__(self, value):
        if hasattr(value, "type") and value.type == "uri":
            self.value = value.value
        else:
            self.value = NSM.uri(value, strip_iri=True)

    def __eq__(self, value):
        test_val = NSM.uri(str(value), strip_iri=True)
        if self.value == test_val:
            return True
        return False

    def __str__(self):
        return self.sparql_uri

class BlankNode(BaseRdfDataType):
    """ URI/IRI class for working with RDF data """
    class_type = "BlankNode"
    type = "bnode"    

    # def __new__(self, value):
    #     pdb.set_trace()
    #     if hasattr(value, "type") and value.type =="uri":
    #         return value
    #     else:
    #         return  self #return str.__new__(cls, *args, **kwargs)

    def __init__(self, value=None):
        if hasattr(value, "type") and value.type == "bnode":
            self.value = value.value
        elif is_not_null(value):
            self.value = value
        else:
            self.value = "_bn_" + new_id()

class XsdString(str, BaseRdfDataType):
    """ String instance of rdf xsd:string type value"""

    datatype = "xsd:string"
    class_type = "XsdString"
    py_type = str

    def __new__(cls, *args, **kwargs):
        if hasattr(args[0], "class_type") and args[0].class_type == "XsdString":
            return args[0]
        else: 
            if "lang" in kwargs.keys():
                lang = kwargs.pop("lang")
            else:
                lang = None
            newobj = str.__new__(cls, *args, **kwargs)
            newobj.lang = lang
        return newobj

    def __init__(self, *args, **kwargs):
        self.value = str(self)

    def __repr__(self):
        return self._format(method="sparql")

    def __add__(self, other):
        if hasattr(other, "datatype"):
            rtn_lang = None
            pdb.set_trace()
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

class XsdBoolean(BaseRdfDataType):
    """ Boolean instance of rdf xsd:boolean type value"""

    datatype = "xsd:boolean"
    class_type = "XsdBoolean"
    py_type = bool

    def __init__(self, value):
        if hasattr(value, "class_type") and value.class_type == "XsdBoolean":
            self.value = bool(self.value)
        else:
            self.value = cbool(str(value))

    def __eq__(self, value):
        if value == self.value:
            return True
        elif value != self.value:
            return False

    def __bool__(self):
        pdb.set_trace()
        if self.value is None:
            return False
        return self.value

class XsdDate(date, BaseRdfDataType):
    """ Datetime Date instacne of rdf xsd:date type value"""

    datatype = "xsd:date"
    class_type = "XsdDate"
    py_type = date

    def __new__(cls, *args, **kwargs):
        if hasattr(args[0], "class_type") and args[0].class_type == "XsdDate":
            return args[0]
        else:
            yy = args[0]
            mm = args[1:2][0] if args[1:2] else 0
            dd = args[2:3][0] if args[2:3] else 0
            if isinstance(args[0], str):
                yy = parse(args[0])
            if isinstance(yy, date) or isinstance(yy, datetime):
                dd = yy.day
                mm = yy.month
                yy = yy.year
        return date.__new__(cls, yy, mm, dd, **kwargs)

    def __init__(self, *args, **kwargs):
        self.value = self

class XsdDatetime(datetime, BaseRdfDataType):
    """ Datetime Datetime instance of rdf xsd:datetime type value"""

    datatype = "xsd:datetime"
    class_type = "XsdDatetime"
    py_type = datetime

    def __new__(cls, *args, **kwargs):
        if hasattr(args[0], "class_type") and \
                args[0].class_type == "XsdDatetime":
            return args[0]
        else:
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
        return datetime.__new__(cls, *vals, **kwargs)

    def __init__(self, *args, **kwargs):
        self.value = self

class XsdTime(time, BaseRdfDataType):
    """ Datetime Datetime instance of rdf xsd:datetime type value"""

    datatype = "xsd:time"
    class_type = "XsdTime"
    py_type = time

    def __new__(cls, *args, **kwargs):
        if hasattr(args[0], "class_type") and \
                args[0].class_type == "XsdTime":
            return args[0]
        else:
            hh = args[0]
            mi = args[1:2][0] if args[1:2] else 0
            ss = args[2:3][0] if args[2:3] else 0
            ms = args[3:4][0] if args[3:4] else 0
            tz = args[4:5][0] if args[4:5] else timezone.utc
            if isinstance(args[0], str):
                tt = parse(args[0])
            if isinstance(tt, datetime) or isinstance(tt, time):
                tz = tt.tzinfo if tt.tzinfo else timezone.utc
                ms = tt.microsecond
                ss = tt.second
                mi = tt.minute
                hh = tt.hour
            vals = tuple([hh, mi, ss, ms, tz])
        return time.__new__(cls, *vals, **kwargs)

    def __init__(self, *args, **kwargs):
        self.value = self

class XsdInteger(int, BaseRdfDataType):
    """ Integer instance of rdf xsd:string type value"""

    datatype = "xsd:integer"
    class_type = "XsdInteger"
    py_type = int

    def __new__(cls, *args, **kwargs):
        if hasattr(args[0], "class_type") and \
                args[0].class_type == "XsdInteger":
            return args[0]
        else: 
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
            if other.datatype == "xsd:integer":
                rtn_val = self.value + other.value 
            else:
                rtn_val = self.value + other.value
        else:
            rtn_val = self.value + other
        return XsdInteger(rtn_val) 

    def __add__(self, other):
        return self._internal_add(other)

    def __iadd__(self, other):
        return self._internal_add(other)

    def __radd__(self, other):
        return self._internal_add(other)


class XsdDecimal(Decimal, BaseRdfDataType):
    """ Integer instance of rdf xsd:string type value"""

    datatype = "xsd:decimal"
    class_type = "XsdDecimal"
    py_type = int

    def __new__(cls, *args, **kwargs):
        if hasattr(args[0], "class_type") and \
                args[0].class_type == "XsdDecimal":
            return args[0]
        else:
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
"""
"xsd_anyURI":
        # URI (Uniform Resource Identifier)
"xsd_base64Binary":
        # Binary content coded as "base64"
"xsd_boolean":
        # Boolean (true or false)
"xsd_byte":
        # Signed value of 8 bits
"xsd_date":
        ## Gregorian calendar date
"xsd_dateTime":
        ## Instant of time (Gregorian calendar)
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


xsd_class_list = [Uri,
                  XsdBoolean,
                  XsdDate,
                  XsdDatetime,
                  XsdString,
                  XsdTime,
                  XsdInteger]

DT_LOOKUP = {}
for xsd_class in xsd_class_list:
    attr_list = ["type", "py_type", "class_type"]
    for attr in attr_list:
        if hasattr(xsd_class, attr):
            DT_LOOKUP[getattr(xsd_class, attr)] = xsd_class
    if hasattr(xsd_class, "datatype"):
        DT_LOOKUP[NSM.iri(NSM.uri(xsd_class.datatype))] = xsd_class
        DT_LOOKUP[NSM.clean_iri(NSM.uri(xsd_class.datatype))] = xsd_class
        DT_LOOKUP[NSM.pyuri(xsd_class.datatype)] = xsd_class
        DT_LOOKUP[NSM.ttluri(xsd_class.datatype)] = xsd_class
    DT_LOOKUP[xsd_class] = xsd_class
