import unittest

import yaml

from hepbenchmarksuite.exceptions import PluginBuilderException, PluginMetadataException
from hepbenchmarksuite.plugins.construction.config_builder import ConfigPluginBuilder
from hepbenchmarksuite.plugins.construction.dynamic_metadata_provider import DynamicPluginMetadataProvider
from tests.plugins.registry.optional.plugin import PluginWithOptionalParameter
from tests.plugins.registry.valid.plugin1 import PluginMultipleParameters, PluginParameterless


class TestConfigPluginBuilder(unittest.TestCase):

    def test_build__instantiates_correct_plugins(self):
        raw_config = """
            plugins:
                PluginParameterless: {}
                PluginMultipleParameters:
                    param1: 42
                    param2: value
        """
        config = yaml.safe_load(raw_config)
        plugin_registry = DynamicPluginMetadataProvider('tests/plugins/registry/valid')
        plugin_builder = ConfigPluginBuilder(config['plugins'], plugin_registry)

        plugins = plugin_builder.build()

        num_plugins_in_config = 2
        self.assertEqual(num_plugins_in_config, len(plugins))

        plugin = plugins[0]
        self.assertTrue(isinstance(plugin, PluginParameterless))

        plugin = plugins[1]
        self.assertTrue(isinstance(plugin, PluginMultipleParameters))
        # Check correct config is passed to the constructor
        self.assertEqual(42, plugin.param1)
        self.assertEqual('value', plugin.param2)

    def test_build__unknown_plugin(self):
        raw_config = """
            plugins:
                UnregisteredPlugin: {}
        """
        config = yaml.safe_load(raw_config)
        plugin_registry = DynamicPluginMetadataProvider('tests/plugins/registry/valid')
        plugin_builder = ConfigPluginBuilder(config['plugins'], plugin_registry)

        self.assertRaises(PluginMetadataException, plugin_builder.build)

    def test_build__superfluous_parameter(self):
        raw_config = """
            plugins:
                PluginParameterless:
                    param: 42
        """
        config = yaml.safe_load(raw_config)
        plugin_registry = DynamicPluginMetadataProvider('tests/plugins/registry/valid')
        plugin_builder = ConfigPluginBuilder(config['plugins'], plugin_registry)

        self.assertRaises(PluginBuilderException, plugin_builder.build)

    def test_build__unrecognized_parameter(self):
        raw_config = """
            plugins:
                PluginSingleParameter:
                    unrecognized: 42
        """
        config = yaml.safe_load(raw_config)
        plugin_registry = DynamicPluginMetadataProvider('tests/plugins/registry/valid')
        plugin_builder = ConfigPluginBuilder(config['plugins'], plugin_registry)

        self.assertRaises(PluginBuilderException, plugin_builder.build)

    def test_build__missing_parameter(self):
        raw_config = """
               plugins:
                   PluginSingleParameter: {}
           """
        config = yaml.safe_load(raw_config)
        plugin_registry = DynamicPluginMetadataProvider('tests/plugins/registry/valid')
        plugin_builder = ConfigPluginBuilder(config['plugins'], plugin_registry)

        self.assertRaises(PluginBuilderException, plugin_builder.build)

    def test_build__matches_case_insensitively(self):
        raw_config = """
               plugins:
                   pluginparameterless: {}
                   
           """
        config = yaml.safe_load(raw_config)
        plugin_registry = DynamicPluginMetadataProvider('tests/plugins/registry/valid')
        plugin_builder = ConfigPluginBuilder(config['plugins'], plugin_registry)

        plugins = plugin_builder.build()
        self.assertEqual(1, len(plugins))

    def test_build__optional_parameters(self):
        raw_config = """
               plugins:
                   PluginWithOptionalParameter:
                       mandatory: 42
           """
        config = yaml.safe_load(raw_config)
        plugin_registry = DynamicPluginMetadataProvider('tests/plugins/registry/optional')
        plugin_builder = ConfigPluginBuilder(config['plugins'], plugin_registry)

        plugins = plugin_builder.build()

        self.assertEqual(1, len(plugins))

        plugin = plugins[0]
        self.assertTrue(isinstance(plugin, PluginWithOptionalParameter))
        self.assertEqual(plugin.mandatory, 42)
        self.assertEqual(plugin.optional, -1)
