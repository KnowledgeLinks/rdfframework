import unittest

import rdfframework.configuration.rdfwconfig as configuration

class TestConfigSingleton(unittest.TestCase):

    def setUp(self):
        pass

    def test_init(self):
        new_config = configuration.ConfigSingleton("", tuple(), dict())
        self.assertIsInstance(
            new_config, 
            configuration.ConfigSingleton)

    def tearDown(self):
        pass


class TestRdfConfigManagerInitialization(unittest.TestCase):

    def setUp(self):
        self.config_mgr = configuration.RdfConfigManager()

    def test_init_no_params(self):
        self.assertIsInstance(self.config_mgr,
                              configuration.RdfConfigManager)

    def test_init_values(self):
        self.assertFalse(self.config_mgr.is_initialized)
        self.assertFalse(self.config_mgr.locked)


    def tearDown(self):
        pass


class TestRdfConfigManagerInitSimpleConfig(unittest.TestCase):

    def setUp(self):
        self.config = {"base_url": "http://example.org/"}


    def test_simple_config(self):
        config_mgr = configuration.RdfConfigManager(self.config)
        self.assert_(config_mgr.base_url)
        
    def tearDown(self):
        pass
