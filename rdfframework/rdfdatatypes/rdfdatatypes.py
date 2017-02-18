import json
import pdb
from rdfframework.utilities import get_ns_obj as nsm

class BaseRdfDataType(object):
    """ Base for all rdf datatypes. Not designed to be used alone """
    type = "literal"

    def __init__(self, value):
        self.value = value

    def _format(self, method="sparql", dt_format="turtle"):
        """ formats the value """

        try:
            rtn_val = json.dumps(self.value)
        except:
            rtn_val = str(self.value)
        if self.type == 'literal':
            if hasattr(self, "datatype"):
                if hasattr(self, "lang") and self.lang:
                    rtn_val += "@%s" % self.lang
                else:
                    dt = self.datatype
                    print("dt_format: ", dt_format)
                    if dt_format == "uri":
                        dt = nsm().uri(self.datatype)
                    if method == "sparql":
                        rtn_val += "^^%s" % dt
            else:
                rtn_val += "^^xsd:string"
        elif self.type == 'uri':
            rtn_val = nsm.ttluri(self.value)
        return rtn_val

    def __repr__(self):
        return self._format(method="sparql")

    @property
    def sparql(self):
        return self._format(method="sparql")

    @property
    def sparql_uri(self):
        return self._format(method="sparql", dt_format="uri")

class XsdString(str, BaseRdfDataType):
    """ String instance of rdf xsd:string type value"""

    datatype = "xsd:string"
    class_type = "XsdString"

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