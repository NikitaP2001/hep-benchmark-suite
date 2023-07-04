import logging
from collections import defaultdict
from typing import List

from hepbenchmarksuite.plugins.construction.builder import PluginBuilder
from hepbenchmarksuite.plugins.execution.executor import RootPluginExecutor, LeafPluginExecutor
from hepbenchmarksuite.plugins.execution.strategy import ThreadExecutionStrategy
from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin


class PluginRunner:
    """
    Manages the instances of stateful plugins, starts and stops them and
    collects their results.
    """

    def __init__(self, plugin_builder: PluginBuilder):
        self.plugin_builder = plugin_builder
        self.results = defaultdict(dict)
        self.executor = None
        self.plugins = None
        self.are_plugins_started = False

    def start_plugins(self):
        assert not self.are_plugins_started
        logging.info('Starting plugins...')

        if self.executor is None:
            self.plugins = self.plugin_builder.build()
            self.executor = self._create_plugin_executor(self.plugins)
        self.executor.start_plugins()

        self.are_plugins_started = True

    def _create_plugin_executor(self, plugins: List[StatefulPlugin]) -> RootPluginExecutor:
        leaf_executor = LeafPluginExecutor(plugins, ThreadExecutionStrategy)
        # Use the following if the plugin threads should run in a separate process
        # composite_executor = CompositePluginExecutor(leaf_executor, ProcessExecutionStrategy)
        root_executor = RootPluginExecutor(leaf_executor)
        return root_executor

    def stop_plugins(self, period: str):
        assert self.are_plugins_started

        self.executor.stop_plugins()
        self._collect_plugin_results(period)

        self.are_plugins_started = False
        logging.info(f'Plugin stage "{period}" finished.')

    def _collect_plugin_results(self, period: str):
        for plugin in self.plugins:
            plugin_name = type(plugin).__name__

            if period in self.results[plugin_name]:
                raise ValueError(f'Results for the "{period}" period already exist. '
                                 f'Results would be overwritten."')

            result = plugin.get_result()
            if result['status'] == 'failed':
                logging.error(f'Plugin "{plugin_name}" failed: {result["error_message"]}')

            self.results[plugin_name][period] = result

    def get_results(self):
        return self.results
