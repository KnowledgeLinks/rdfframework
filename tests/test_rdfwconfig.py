import unittest
import pdb
import rdfframework.configuration.rdfwconfig as configuration
import logging
configuration.log.setLevel(logging.CRITICAL)

class TestConfigSingleton(unittest.TestCase):

    def setUp(self):
        configuration.ConfigSingleton._instances = {}

    def test_init(self):
        new_config = configuration.ConfigSingleton("", tuple(), dict())
        self.assertIsInstance(
            new_config,
            configuration.ConfigSingleton)

    def tearDown(self):
        configuration.ConfigSingleton._instances = {}



class TestRdfConfigManagerInitialization(unittest.TestCase):

    def setUp(self):
        configuration.RdfConfigManager.clear()
        self.config_mgr = configuration.RdfConfigManager()

    def test_init_no_params(self):
        self.assertIsInstance(self.config_mgr,
                              configuration.RdfConfigManager)

    def test_init_values(self):
        self.assertFalse(self.config_mgr.__is_initialized__)
        self.assertFalse(self.config_mgr.__locked__)

    def tearDown(self):
        pass


class TestRdfConfigManagerInitSimpleConfig(unittest.TestCase):

    def setUp(self):
        configuration.RdfConfigManager.clear()
        self.config = {"base_url": "http://example.org/"}


    def test_simple_config(self):
        config_mgr = configuration.RdfConfigManager(self.config, verify=False)
        self.assertEqual(
            config_mgr.base_url,
            self.config.get("base_url"))

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
