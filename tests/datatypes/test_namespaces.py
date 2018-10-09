import unittest
import pdb
import rdfframework.datatypes as rdt

class TestUri(unittest.TestCase):

    def setUp(self):
        self.nsm = rdt.RdfNsManager()
        self.test_equal_values = ("xsd:string",
                                  "xsd_string",
                                  "XSD:string",
                                  "http://www.w3.org/2001/XMLSchema#string",
                                  "<http://www.w3.org/2001/XMLSchema#string>",
                                  self.nsm.xsd.string)
        self.test_not_eq_values = ("xsd:string",
                                   "xsd_strings",
                                   "http://www.w3.org/2001/XMLSchema#string",
                                   rdt.RdfNsManager().xsd.strings)
        self.test_outputs_test_uri = self.nsm.xsd.string
        self.test_outputs = (('sparql', 'xsd:string'),
                             ('sparql_uri',
                              '<http://www.w3.org/2001/XMLSchema#string>'),
                             ('clean_uri',
                              'http://www.w3.org/2001/XMLSchema#string'),
                             ('pyuri', 'xsd_string'))
        self.test_no_ns_outputs_test_uri = rdt.Uri("http://test.com/test")
        self.test_no_ns_outputs = (('sparql', '<http://test.com/test>'),
                                   ('sparql_uri', '<http://test.com/test>'),
                                   ('clean_uri', 'http://test.com/test'),
                                   ('pyuri',
                                    'pyuri_aHR0cDovL3Rlc3QuY29tLw==_test'))
        self.test_no_ns_inputs = ('<http://test.com/test>',
                                  'http://test.com/test',
                                  'pyuri_aHR0cDovL3Rlc3QuY29tLw==_test',
                                  rdt.Uri('<http://test.com/test>'))

    def test_equal_inputs(self):
        self.assertTrue(all(rdt.Uri(x)==rdt.Uri(self.test_equal_values[0]) \
                            for x in self.test_equal_values))

    def test_not_equal_inputs(self):
        self.assertFalse(all(rdt.Uri(x)==rdt.Uri(self.test_not_eq_values[0]) \
                            for x in self.test_not_eq_values))

    def test_uri_as_arg_returns_uri(self):
        test_uri = self.nsm.xsd.test
        self.assertEqual(id(test_uri), id(rdt.Uri(test_uri)))

    def test_ouput_formats(self):
        test_uri = self.test_outputs_test_uri
        for args in self.test_outputs:
            self.assertEqual(getattr(test_uri, args[0]), args[1],
                             "format='%s'" % args[0])

    def test_no_ns_ouput_formats(self):
        test_uri = self.test_no_ns_outputs_test_uri
        for args in self.test_no_ns_outputs:
            self.assertEqual(getattr(test_uri, args[0]), args[1],
                             "format='%s'" % args[0])

    def test_no_ns_inputs(self):
        first = rdt.Uri(self.test_no_ns_inputs[0])
        for val in self.test_no_ns_inputs:
            self.assertEqual(rdt.Uri(val), first,
                             "\ninput value: %s" % val)

    def tearDown(self):
        pass



# class TestRdfConfigManagerInitialization(unittest.TestCase):

#     def setUp(self):
#         configuration.RdfConfigManager.clear()
#         self.config_mgr = configuration.RdfConfigManager()

#     def test_init_no_params(self):
#         self.assertIsInstance(self.config_mgr,
#                               configuration.RdfConfigManager)

#     def test_init_values(self):
#         self.assertFalse(self.config_mgr.is_initialized)
#         self.assertFalse(self.config_mgr.locked)


#     def tearDown(self):
#         pass


# class TestRdfConfigManagerInitSimpleConfig(unittest.TestCase):

#     def setUp(self):
#         configuration.RdfConfigManager.clear()
#         self.config = {"base_url": "http://example.org/"}


#     def test_simple_config(self):
#         config_mgr = configuration.RdfConfigManager(self.config)
#         self.assertEqual(
#             config_mgr.base_url,
#             self.config.get("base_url"))

#     def tearDown(self):
#         pass

if __name__ == '__main__':
    unittest.main()
