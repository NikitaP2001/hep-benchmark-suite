import time
import unittest
from unittest.mock import Mock

from hepbenchmarksuite.plugins.execution.strategy import ProcessExecutionStrategy, ExecutionStrategy
from hepbenchmarksuite.plugins.execution.executor import LeafPluginExecutor, CompositePluginExecutor, RootPluginExecutor
from hepbenchmarksuite.plugins.registry.test_plugin import TestPlugin


class AnotherTestPlugin(TestPlugin):
    pass


class DummyExecutionStrategy(ExecutionStrategy):

    def start(self, target_func, args):
        target_func(args)

    def join(self):
        pass


class TestLeafPluginExecutor(unittest.TestCase):

    def test_start_plugins__starts_processes(self):
        plugins = [TestPlugin() for _ in range(3)]
        executor = LeafPluginExecutor(plugins, ProcessExecutionStrategy)
        root_executor = RootPluginExecutor(executor)

        self.assertEqual(len(executor.workers), 0)

        root_executor.start_plugins()

        self.assertEqual(len(executor.workers), 3)

        # Assert the processes were actually started
        for worker in executor.workers:
            self.assertTrue(isinstance(worker, ProcessExecutionStrategy))
            self.assertTrue(worker.process.is_alive())

        # Clean up
        self._terminate_processes(executor)

    @staticmethod
    def _terminate_processes(executor: LeafPluginExecutor):
        for worker in executor.workers:
            worker.process.terminate()

    def test_stop_plugins__stops_processes(self):
        plugins = [TestPlugin() for _ in range(3)]
        executor = LeafPluginExecutor(plugins, ProcessExecutionStrategy)
        root_executor = RootPluginExecutor(executor)
        root_executor.start_plugins()

        root_executor.stop_plugins()

        self.assertEqual(len(executor.workers), 0)

    def test_multiple_plugins__returns_correct_results(self):
        plugins = [
            TestPlugin(),
            AnotherTestPlugin()
        ]
        executor = LeafPluginExecutor(plugins, ProcessExecutionStrategy)
        root_executor = RootPluginExecutor(executor)
        root_executor.start_plugins()

        # Wait for plugins to collect measurements.
        time.sleep(1)

        root_executor.stop_plugins()

        for plugin in plugins:
            plugin_result = plugin.get_result()
            count_measurement = list(plugin_result['measurements'].values())[0]
            self.assertNotEqual(0, count_measurement,
                                'The results of the plugin should be propagated to the '
                                'parent process.')


class TestCompositePluginExecutor(unittest.TestCase):

    def test_start_plugins__forwards_to_nested(self):
        mock_nested_executor = Mock()
        executor = CompositePluginExecutor(mock_nested_executor, DummyExecutionStrategy)
        root_executor = RootPluginExecutor(executor)

        root_executor.start_plugins()

        mock_nested_executor.start_plugins.assert_called_once()

    def test_start_plugins__starts_inside_worker(self):
        mock_nested_executor = Mock()
        executor = CompositePluginExecutor(mock_nested_executor, Mock)
        root_executor = RootPluginExecutor(executor)

        root_executor.start_plugins()

        executor.worker.start.assert_called_once()

    def test_stop_plugins__stops_worker(self):
        mock_nested_executor = Mock()
        executor = CompositePluginExecutor(mock_nested_executor, Mock)
        root_executor = RootPluginExecutor(executor)
        root_executor.start_plugins()

        root_executor.plugins_started.set()

        root_executor.stop_plugins()

        executor.worker.join.assert_called_once()
