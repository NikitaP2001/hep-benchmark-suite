import unittest

from hepbenchmarksuite.plugins.construction.metadata_provider import PluginParameter
from hepbenchmarksuite.plugins.construction.dynamic_metadata_provider import DynamicPluginMetadataProvider
from tests.plugins.registry.valid.plugin1 import PluginParameterless, PluginMultipleParameters
from tests.plugins.registry.valid.plugin2 import PluginSingleParameter


class TestDynamicPluginMetadataProvider(unittest.TestCase):

    def test_initialize__registers_plugins_successfully(self):
        """
        Tests that all plugins in the directory in multiple
        files are all loaded including their expected parameters.
        """
        metadata_path = 'tests/plugins/registry/valid'
        metadata_provider = DynamicPluginMetadataProvider(metadata_path)

        metadata_provider.initialize()

        plugins_metadata = metadata_provider.get_items()

        # Three plugins should be registered
        self.assertEqual(3, len(plugins_metadata))

        # The right plugin names are registered
        expected_plugin_names = {PluginParameterless.__name__,
                                 PluginSingleParameter.__name__,
                                 PluginMultipleParameters.__name__}
        registered_plugin_names = set([item.get_name() for item in plugins_metadata])
        self.assertSetEqual(expected_plugin_names, registered_plugin_names)

        # Parameters are also registered
        item = metadata_provider.get_item_by_name(PluginParameterless.__name__)
        self.assertEqual(0, len(item.get_parameters()))

        item = metadata_provider.get_item_by_name(PluginSingleParameter.__name__)
        params = item.get_parameters()
        self.assertEqual(1, len(params))
        self._assert_params_equal(params[0], PluginParameter('param', is_optional=False))

        item = metadata_provider.get_item_by_name(PluginMultipleParameters.__name__)
        params = item.get_parameters()
        self.assertEqual(2, len(params))
        self._assert_params_equal(PluginParameter('param1', is_optional=False), params[0])
        self._assert_params_equal(PluginParameter('param2', is_optional=False), params[1])

    def _assert_params_equal(self, param1, param2) -> None:
        self.assertEqual(param1.get_name(), param2.get_name())

    def test_initialize__fails_to_register_non_plugins(self):
        """
        Tests that the registrator ignores to parse a class that does not inherit
        from StatefulPlugin.
        """
        metadata_path = 'tests/plugins/registry/invalid'
        metadata_provider = DynamicPluginMetadataProvider(metadata_path)

        metadata_provider.initialize()
        plugins_metadata = metadata_provider.get_items()

        self.assertListEqual(list(), plugins_metadata)

    def test_initialize__succeeds_quietly_with_missing_directory(self):
        """
        Reading from a directory that does not exist means that there
        are no plugins. None should be registered in such a case.
        """
        metadata_path = 'register/non_existent'
        metadata_provider = DynamicPluginMetadataProvider(metadata_path)

        metadata_provider.initialize()
        plugins_metadata = metadata_provider.get_items()

        self.assertListEqual(list(), plugins_metadata)
