import logging
from collections import defaultdict
from typing import List

from hepbenchmarksuite.exceptions import PluginAssertError
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
        self.plugins = []
        self.are_plugins_started = False

    def initialize(self):
        """
        Initializes the plugin runner by instantiating plugins and
        setting up the execution strategy.
        """
        if self.executor is not None:
            raise PluginAssertError('The PluginRunner has already been initialized.')

        self.plugins = self.plugin_builder.build()
        self.executor = self._create_plugin_executor(self.plugins)

    def has_plugins(self) -> bool:
        return len(self.plugins) > 0

    def start_plugins(self):
        """
        Starts plugins in the background in either threads or processes.
        The plugins must not yet be started when this method is called.
        """
        assert not self.are_plugins_started

        logging.debug('Starting plugins...')

        self.executor.start_plugins()

        self.are_plugins_started = True

    def _create_plugin_executor(self, plugins: List[StatefulPlugin]) -> RootPluginExecutor:
        leaf_executor = LeafPluginExecutor(plugins, ThreadExecutionStrategy)
        # Use the following if the plugin threads should run in a separate process
        # composite_executor = CompositePluginExecutor(leaf_executor, ProcessExecutionStrategy)
        root_executor = RootPluginExecutor(leaf_executor)
        return root_executor

    def stop_plugins(self, period: str):
        """
        Stops plugins and waits for them to finish.
        The plugins must be running when this function is called.

        Args:
            period: The name of the plugin stage. Multiple plugin runs
            are tracked using this variable.
        """
        assert self.are_plugins_started

        self.executor.stop_plugins()
        self._collect_plugin_results(period)

        self.are_plugins_started = False
        logging.debug('Plugin stage "%s" finished.', period)

    def _collect_plugin_results(self, period: str):
        for plugin in self.plugins:
            plugin_name = type(plugin).__name__

            if period in self.results[plugin_name]:
                raise ValueError(f'Results for the "{period}" period already exist. '
                                 f'Results would be overwritten."')

            result = plugin.get_result()
            if result['status'] == 'failure':
                logging.error('Plugin "%s" failed: %s', plugin_name, result["error_message"])
                logging.debug('Traceback: %s', result["traceback"])

            self.results[plugin_name][period] = result

    def are_plugins_running(self) -> bool:
        return self.are_plugins_started

    def get_results(self):
        return self.results
