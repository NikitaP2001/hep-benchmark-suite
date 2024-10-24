import time
import unittest
from typing import List

from hepbenchmarksuite.plugins.execution.executor import LeafPluginExecutor, CompositePluginExecutor, RootPluginExecutor
from hepbenchmarksuite.plugins.execution.strategy import ThreadExecutionStrategy, ProcessExecutionStrategy
from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin
from tests.pytests.plugins.dummy_timeseries_plugin import DummyTimeseriesPlugin


class DummyTimeseriesPlugin2(DummyTimeseriesPlugin):
    pass


def repeat(times: int):
    def decorater(func):
        def wrapper(*args, **kwargs):
            for i in range(0, times):
                func(*args, **kwargs)

        return wrapper

    return decorater


class TestPluginExecutors(unittest.TestCase):

    def _get_plugins(self) -> List[StatefulPlugin]:
        """
        Returns:
            A few dummy plugins that run every 50 ms.
        """
        plugins = [
            DummyTimeseriesPlugin2(interval_mins=0.05 / 60),
            DummyTimeseriesPlugin(interval_mins=0.05 / 60)
        ]
        return plugins

    def _test_executors(self, executor: RootPluginExecutor,
                        plugins: List[StatefulPlugin],
                        work_time_secs: float):
        """
        Tests the synchronization of the plugin execution.

        Each individual plugin may be set up to run inside its own thread,
        which in turn is created by a parent process, which was created by
        the root process: Root process -> Plugin processes -> Plugin thread.
        The processes and plugins need to be synchronized such that the
        correct results from plugins are retrieved.
        """
        executor.start_plugins()

        # Let the plugins work for a short while.
        time.sleep(work_time_secs)

        executor.stop_plugins()

        test_plugin_result = plugins[0].get_result()
        self.assertGreater(len(test_plugin_result['values']), 0,
                           'At least some measurements should have been collected.')

        timeseries_plugin_result = plugins[1].get_result()
        self.assertGreater(len(timeseries_plugin_result['values']), 0,
                           'At least some measurements should have been collected.')

    @repeat(10)
    def test_nested_plugin_executors(self):
        """
        Tests the following setup: Main process -> Plugins process -> Plugin threads.
        """
        plugins = self._get_plugins()

        leaf_executor = LeafPluginExecutor(plugins, ThreadExecutionStrategy)
        composite_executor = CompositePluginExecutor(leaf_executor, ProcessExecutionStrategy)
        executor = RootPluginExecutor(composite_executor)

        self._test_executors(executor, plugins, work_time_secs=0.3)

    @repeat(10)
    def test_leaf_only_executor_with_threads(self):
        """
        Tests the following setup: Main process -> Plugin threads.
        """
        plugins = self._get_plugins()

        leaf_executor = LeafPluginExecutor(plugins, ThreadExecutionStrategy)
        executor = RootPluginExecutor(leaf_executor)

        self._test_executors(executor, plugins, work_time_secs=0.3)

    @repeat(10)
    def test_leaf_only_executor_with_processes(self):
        """
        Tests the following setup: Main process -> Plugin processes.
        """
        plugins = self._get_plugins()

        leaf_executor = LeafPluginExecutor(plugins, ProcessExecutionStrategy)
        executor = RootPluginExecutor(leaf_executor)

        self._test_executors(executor, plugins, work_time_secs=0.3)

    @repeat(10)
    def test_multiple_compositor_hierarchy(self):
        """
        Tests the following setup:
        Main process -> Plugins process -> Additional process -> Plugin threads.
        """
        plugins = self._get_plugins()

        leaf_executor = LeafPluginExecutor(plugins, ThreadExecutionStrategy)
        composite_executor1 = CompositePluginExecutor(leaf_executor, ProcessExecutionStrategy)
        composite_executor2 = CompositePluginExecutor(composite_executor1, ProcessExecutionStrategy)
        executor = RootPluginExecutor(composite_executor2)

        self._test_executors(executor, plugins, work_time_secs=0.3)

    def test_executors_run_multiple_times(self):
        """
        Tests that the executors reset their state when they start
        the plugins again, mainly the multiprocessing events in the RootPluginExecutor.
        """
        plugins = [
            DummyTimeseriesPlugin(interval_mins=0.1 / 60)
        ]

        leaf_executor = LeafPluginExecutor(plugins, ThreadExecutionStrategy)
        composite_executor = CompositePluginExecutor(leaf_executor, ProcessExecutionStrategy)
        executor = RootPluginExecutor(composite_executor)

        # Run for the first time
        executor.start_plugins()
        time.sleep(0.2)
        executor.stop_plugins()

        plugin_result = plugins[0].get_result()
        self.assertGreater(len(plugin_result['values']), 0)

        # Run for the second time
        executor.start_plugins()
        time.sleep(0.2)
        executor.stop_plugins()

        plugin_result = plugins[0].get_result()
        self.assertGreater(len(plugin_result['values']), 0)
