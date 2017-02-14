
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
        _temp_value = parse(value)
        if output == "string":
            _date_format = rdfw().app['kds_dataFormats'].get(\
                    'kds_pythonDateFormat', '')
            return _temp_value.strftime(_date_format)
        elif output == "python":
            return _temp_value
"xsd_dateTime":
        ## Instant of time (Gregorian calendar)
        _temp_value = parse(value)
        if output == "string":
            _date_format = rdfw().app['kds_dataFormats'].get(\
                    'kds_pythonDateTimeFormat', "%Y-%m-%dT%H:%M:%SZ")
            if _date_format:
                return _temp_value.strftime(_date_format)
            else:
                return str(_temp_value)
        elif output == "python":
            return _temp_value
"xsd_decimal":
        # Decimal numbers
        return float(value)
"xsd_double":
        # IEEE 64
        return float(value)
"xsd_duration":
        # Time durations
        return timedelta(milleseconds=float(value))
"xsd_ENTITIES":
        # Whitespace
        return value
"xsd_ENTITY":
        # Reference to an unparsed entity
        return value
"xsd_float":
        # IEEE 32
        return float(value)
"xsd_gDay":
        # Recurring period of time: monthly day
        return value
"xsd_gMonth":
        # Recurring period of time: yearly month
        return value
"xsd_gMonthDay":
        # Recurring period of time: yearly day
        return value
"xsd_gYear":
        # Period of one year
        return value
"xsd_gYearMonth":
        # Period of one month
        return value
"xsd_hexBinary":
        # Binary contents coded in hexadecimal
        return value
"xsd_ID":
        # Definition of unique identifiers
        return value
"xsd_IDREF":
        # Definition of references to unique identifiers
        return value
"xsd_IDREFS":
        # Definition of lists of references to unique identifiers
        return value
"xsd_int":
        # 32
        return value
"xsd_integer":
        # Signed integers of arbitrary length
        return int(value)
"xsd_language":
        # RFC 1766 language codes
        return value
"xsd_long":
        # 64
        return int(value)
"xsd_Name":
        # XML 1.O name
        return value
"xsd_NCName":
        # Unqualified names
        return value
"xsd_negativeInteger":
        # Strictly negative integers of arbitrary length
        return abs(int(value))*-1
"xsd_NMTOKEN":
        # XML 1.0 name token (NMTOKEN)
        return value
"xsd_NMTOKENS":
        # List of XML 1.0 name tokens (NMTOKEN)
        return value
"xsd_nonNegativeInteger":
        # Integers of arbitrary length positive or equal to zero
        return abs(int(value))
"xsd_nonPositiveInteger":
        # Integers of arbitrary length negative or equal to zero
        return abs(int(value))*-1
"xsd_normalizedString":
        # Whitespace
        return value
"xsd_NOTATION":
        # Emulation of the XML 1.0 feature
        return value
"xsd_positiveInteger":
        # Strictly positive integers of arbitrary length
        return abs(int(value))
"xsd_QName":
        # Namespaces in XML
        return value
"xsd_short":
        # 32
        return value
"xsd_string":
        # Any string
        return value
"xsd_time":
        # Point in time recurring each day
        return parse(value)
"xsd_token":
        # Whitespace
        return value
"xsd_unsignedByte":
        # Unsigned value of 8 bits
        return value.decode()
"xsd_unsignedInt":
        # Unsigned integer of 32 bits
        return int(value)
"xsd_unsignedLong":
        # Unsigned integer of 64 bits
        return int(value)
"xsd_unsignedShort":
        # Unsigned integer of 16 bits
        return int(value)
    else:
        return value
