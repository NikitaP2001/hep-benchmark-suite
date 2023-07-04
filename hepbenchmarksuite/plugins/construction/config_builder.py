from typing import List

from hepbenchmarksuite.exceptions import PluginBuilderException
from hepbenchmarksuite.plugins.construction.builder import PluginBuilder, PluginConfigItem, PluginConfigParameter
from hepbenchmarksuite.plugins.construction.metadata_provider import PluginMetadataProvider, PluginMetadata
from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin


class ConfigPluginBuilder(PluginBuilder):
    """
    ConfigPluginBuilder instantiates plugins based on the given
    configuration and the plugin metadata provided by the PluginMetadataProvider.
    """

    def __init__(self, config, metadata_provider: PluginMetadataProvider):
        self.config = config
        self.metadata_provider = metadata_provider

    def build(self) -> List[StatefulPlugin]:
        # Read all entries in the configuration (including plugin parameters)
        plugin_config_items = self._read_config()
        # Instantiate those plugins
        plugins = self._instantiate_plugins(plugin_config_items)
        return plugins

    def _read_config(self) -> List[PluginConfigItem]:
        plugin_configs = list()
        for plugin_name, plugin_configuration in self.config.items():
            params = list()
            for param_name, param_value in plugin_configuration.items():
                params.append(PluginConfigParameter(param_name, param_value))
            plugin_configs.append(PluginConfigItem(plugin_name, params))
        return plugin_configs

    def _instantiate_plugins(self, plugin_config_items: List[PluginConfigItem]) -> List[StatefulPlugin]:
        self._check_plugin_names(plugin_config_items)

        plugins = list()
        for plugin_config_item in plugin_config_items:
            plugin_name = plugin_config_item.get_name()
            plugin_metadata = self.metadata_provider.get_item_by_name(plugin_name)

            plugin = self._instantiate_plugin(plugin_config_item, plugin_metadata)
            plugins.append(plugin)
        return plugins

    def _check_plugin_names(self, plugin_config_items: List[PluginConfigItem]) -> None:
        plugin_names = [plugin.get_name() for plugin in plugin_config_items]

        if len(set(plugin_names)) != len(plugin_names):
            raise PluginBuilderException(
                f'Detected duplicate plugins in the configuration.'
                f' Specified plugins: {plugin_names}'
            )

    def _instantiate_plugin(self, plugin_config_item: PluginConfigItem,
                            plugin_metadata: PluginMetadata) -> StatefulPlugin:
        assert (plugin_config_item.get_name().lower() == plugin_metadata.get_name().lower())

        self._check_parameters_match(plugin_config_item, plugin_metadata)

        kwargs = {}
        for param in plugin_config_item.get_parameters():
            kwargs[param.get_name()] = param.value

        class_type = plugin_metadata.class_type

        plugin = class_type(**kwargs)
        return plugin

    def _check_parameters_match(self, plugin_config_item: PluginConfigItem,
                                plugin_metadata: PluginMetadata) -> None:
        """
        Checks that all parameters specified in the configuration
        matches expected parameters by the registered plugins.
        """
        config_item_params = plugin_config_item.get_parameters()
        plugin_params = plugin_metadata.get_parameters()

        config_param_names = [param.get_name() for param in config_item_params]
        plugin_param_names = [param.get_name() for param in plugin_params]

        # Check config params match those in registry and
        # no superfluous exist.
        for config_param in config_item_params:
            if config_param.get_name() not in plugin_param_names:
                raise PluginBuilderException(
                    f'Specified parameter "{config_param.get_name()}" was not '
                    f'expected by the "{plugin_metadata.get_name()}" plugin.'
                )
        # Check that each non-default argument of each registry plugin
        # has been defined in config.
        for plugin_param in plugin_params:
            # Optional parameters are not required in the configuration
            if plugin_param.is_optional():
                continue
            if plugin_param.get_name() not in config_param_names:
                raise PluginBuilderException(
                    f'Non-default argument is expected by the "{plugin_metadata.get_name()}"'
                    f'but missing in the configuration file.'
                )
