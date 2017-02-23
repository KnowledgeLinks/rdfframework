__author__ = "Jeremy Nelson, Mike Stabile"

import json
import os
import rdflib
import sys
import unittest

from unittest.mock import MagicMock, patch

PROJECT_DIR = os.path.abspath(os.curdir)
sys.path.append(PROJECT_DIR)
try:
    from rdfframework.getframework import fw_config
    from rdfframework.utilities.baseutilities import *
    from rdfframework.utilities.uriconvertor import clean_iri
    from rdfframework.utilities.frameworkutilities import uid_to_repo_uri
except ImportError:
    from .rdfframework.getframework import fw_config
    from .rdfframework.utilities.baseutilities import *
    from .rdfframework.utilities.uriconvertor import clean_iri
    from .rdfframework.utilities.frameworkutilities import uid_to_repo_uri
   

class Test_cbool(unittest.TestCase):

    def test_cbool(self):
        self.assertTrue(cbool(True))
        self.assertFalse(cbool(False))
        self.assertEqual(cbool(None), None)
        self.assertEqual(cbool(None, False), None)

    def test_cbool_str_true(self):
        self.assertTrue(cbool('true'))
        self.assertTrue(cbool('1'))
        self.assertTrue(cbool('t'))
        self.assertTrue(cbool('y'))
        self.assertTrue(cbool('yes'))

    def test_cbool_str_false(self):
        self.assertFalse(cbool('false'))
        self.assertFalse(cbool('0'))
        self.assertFalse(cbool('n'))
        self.assertFalse(cbool('no'))

class Test_clean_iri(unittest.TestCase):

    def test_clean_iri(self):
        self.assertEqual(
            clean_iri("<http://example.info/test>"),
            "http://example.info/test")

    def test_clean_iri_fail(self):
        self.assertEqual(
            clean_iri("<http://example.info"),
            "<http://example.info")

class TestDeletePropertyClass(unittest.TestCase):

    def test_delete_property(self):
        delete_property = DeleteProperty()
        self.assertTrue(delete_property.delete)


class Test_fw_config(unittest.TestCase):

    def test_fw_config_is_none(self):
        self.assertEqual(fw_config(),
                         "framework not initialized")

    def test_fw_config_kw(self):
        config = DictClass({"host": "local"})
        self.assertEqual(fw_config(config=config),
                         config)   

class TestIri(unittest.TestCase):

    def test_iri(self):
        self.assertEqual(iri("https://schema.org/Person"), 
                         "<https://schema.org/Person>")
        self.assertEqual(iri("<obi:recipient>"),
                         "<obi:recipient>")

    def test_iri_errors(self):
        #self.assertRaises(TypeError, iri, None)
        self.assertEqual(iri(""),
                         "<>")

    def test_iri_question(self):
        self.assertTrue(iri("?"))

    def test_iri_square_bracket(self):
        self.assertTrue(iri("["))


class Test_is_not_null(unittest.TestCase):

    def test_is_not_null(self):
        self.assertFalse(is_not_null(None))
        self.assertFalse(is_not_null(""))

    def test_is_not_null_true(self):
        self.assertTrue(is_not_null("Test"))
        self.assertTrue(is_not_null(1234))      

class Test_make_list(unittest.TestCase):

    def test_make_list_dict(self):
        test_coordinates = { "x": 1, "y": 2}
        self.assertEqual(make_list(test_coordinates),
                         [test_coordinates,])
        
    def test_make_list_list(self):
        test_list = [1,2,3,4]
        self.assertEqual(make_list(test_list),
                         test_list)

    def test_make_list_str(self):
        test_str = "this is a string"
        self.assertEqual(make_list(test_str),
                         [test_str,])

class Test_make_set(unittest.TestCase):

    def test_make_set_str(self):
        test_str = "this is a test"
        self.assertEqual(make_set(test_str),
                         set([test_str,]))

    def test_make_set_list(self):
        test_list = ["ab", "cd"]
        self.assertEqual(make_set(test_list),
                         set(test_list))

    def test_make_set_set(self):
        test_set = set(range(0,5))
        self.assertEqual(make_set(test_set),
                         test_set)


class Test_make_triple(unittest.TestCase):

    def setUp(self):
        self.SCHEMA = rdflib.Namespace("https://schema.org/")

    def test_triple(self):
        subject = rdflib.URIRef("http://peopleuid.com/42")
        object_ = rdflib.Literal("Josey McNamera")
        self.assertEqual(
            make_triple(subject, self.SCHEMA.name, object_),
            "{0} {1} {2} .".format(subject, self.SCHEMA.name, object_))


class TestNotInFormClass(unittest.TestCase):

    def test_notinform(self):
        notInForm = NotInFormClass()
        self.assertTrue(notInForm.notInForm)

class Test_remove_null(unittest.TestCase):

    def test_remove_null_list(self):
        self.assertEqual(remove_null([1, None, 2]),
            [1,2])

    def test_remove_null_set(self):
        self.assertEqual(remove_null(set([None, 1])),
            set([1,]))

    def test_remove_null_no_null(self):
        self.assertEqual(remove_null([1,2]),
            [1,2])
                 
class Test_slugify(unittest.TestCase):

    def test_str_1(self):
        self.assertEqual(
            slugify("Hello Moon"),
            "hello-moon")
 
    def test_num(self):
        self.assertEqual(
            slugify("12 Person"),
            "12-person")

    def test_non_alphanum(self):
        self.assertEqual(
            slugify("N$ one"),
            "n-one")

class Test_nz(unittest.TestCase):

    def test_nz_none(self):
        self.assertEqual(
           nz(None, "a test"),
           "a test")

    def test_nz_empty_str_none_val(self):
        self.assertEqual(
            nz(None, ""),
            "")

    def test_nz_empty_str_val(self):
        self.assertEqual(
            nz("", "a test"),
            "")

    def test_nz_empty_str_val_strict(self):
        self.assertEqual(
            nz("", "a test", False),
            "a test")

class Test_render_without_request(unittest.TestCase):

   def test_template_1(self):
        result = render_without_request(
                     "jsonApiQueryTemplate.rq")
        self.assertTrue(len(result) > 0)

   def test_nonexistent_template(self):
        from jinja2.exceptions import TemplateNotFound
        self.assertRaises(
                TemplateNotFound,
                render_without_request,
                "test.html")


class Test_uid_to_repo_uri(unittest.TestCase):

    @patch("rdfframework.utilities.frameworkutilities.CONFIG")
    def test_good_uid(self, config):
        config.get = MagicMock(return_value="http://test/fedora/rest") 
        self.assertEqual(
            uid_to_repo_uri("7f70bee2-1e24-4c35-9078-c6efbfa30aaf"),
            "http://test/fedora/rest/7f/70/be/e2/7f70bee2-1e24-4c35-9078-c6efbfa30aaf")

class Test_xsd_to_python(unittest.TestCase):

    def setUp(self):
        self.SCHEMA = rdflib.Namespace("https://schema.org/")
        self.XSD = rdflib.XSD

    def test_xsd_in_datatype(self):
        self.assertEqual(
            xsd_to_python("More than a string",
                          str(XSD.string)),
            "More than a string")

    def test_absent_xsd_in_datatype(self):
        self.assertEqual(
            xsd_to_python("More than a string",
                "xsd_string"),
            "More than a string")

    def test_none_value(self):
        self.assertIsNone(
            xsd_to_python(None,
                "xsd_string"))

    def test_uri_rdftype(self):
        self.assertEqual(
            xsd_to_python(str(self.SCHEMA.name),
                str(XSD.url),
                "uri"),
            "<{}>".format(self.SCHEMA.name))

    def test_xsd_anyURI_datatype(self):
        self.assertEqual(
            xsd_to_python(str(self.SCHEMA.description),
                         "xsd_anyURI"),
            str(self.SCHEMA.description))

    def test_xsd_anyURI_datatype_invalid_uri(self):
        #! This passes but should we validate as a URI
        bad_uri = "This is a string pretending to a URI"
        self.assertEqual(
            xsd_to_python(bad_uri,
                "xsd_anyURI"),
            bad_uri)

    def test_xsd_base64Binary(self):
        import base64
        base_64_value = base64.b64encode(b'This some base 64 encoded data')
        self.assertEqual(
            xsd_to_python(base_64_value,
                "xsd_base64Binary"),
                base64.b64decode(base_64_value))

    def test_xsd_boolean(self):
        self.assertTrue(
            xsd_to_python(
                "true",
                "xsd_boolean"))
        self.assertFalse(
            xsd_to_python(
                "false",
                "xsd_boolean"))

    def test_xsd_boolean_str(self):
        self.assertEqual(
            xsd_to_python(
                "true",
                "xsd_boolean",
                output="string"),
            "true")
        self.assertEqual(
            xsd_to_python(
                "False",
                "xsd_boolean",
                output="string"),
            "false")

    def test_xsd_byte(self):
        self.assertEqual(
            xsd_to_python(
                b"1",
                "xsd_byte"),
            "1")


            
            
