import json

from rdfframework.utilities import NS_OBJ as nsm

class BaseRdfDataType(object):
    """ Base for all rdf datatypes. Not designed to be used alone """
    type = "literal"

    def __init__(self, value):
        self.value = value

    def _format(self, method="sparql"):
        """ formats the value """

        try:
            rtn_val = json.dumps(self.value)
        except:
            rtn_val = str(self.value)

        if self.type == 'literal':
            if hasattr(self, "datatype"):
                rtn_val += "^^%s" % self.datatype
            else:
                rtn_val += "^^xsd:string"
        elif self.type == 'uri':
            rtn_val = nsm.ttluri(self.value)

    @property
    def sparql(self):
        return self._format(method="sparql")

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