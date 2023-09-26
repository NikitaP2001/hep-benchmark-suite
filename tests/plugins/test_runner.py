import time
import unittest
from typing import List

from hepbenchmarksuite.plugins.construction.builder import PluginBuilder
from hepbenchmarksuite.plugins.runner import PluginRunner
from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin
from tests.plugins.dummy_timeseries_plugin import DummyTimeseriesPlugin


class DummyPluginBuilder(PluginBuilder):

    def build(self) -> List[StatefulPlugin]:
        plugins = [
            DummyTimeseriesPlugin(interval_mins=0.1 / 60)
        ]
        return plugins


class TestPluginRunner(unittest.TestCase):

    def test_runner(self):
        """
        Tests that the runner orchestrates the plugins as expected,
        including results collection and saving in the appropriate
        format.
        """
        builder = DummyPluginBuilder()
        runner = PluginRunner(builder)
        runner.initialize()

        runner.start_plugins()

        # Let the plugins run for a little while.
        time.sleep(0.2)

        period_name = 'test'
        runner.stop_plugins(period_name)
        results = runner.get_results()

        plugin_name = DummyTimeseriesPlugin.__name__
        plugin_results = results[plugin_name]
        measurements = plugin_results[period_name]['values']

        self.assertGreater(len(measurements), 0)

    def test_runner__fails_with_same_period(self):
        """
        Results collection must fail, otherwise results would be
        overwritten.
        """
        builder = DummyPluginBuilder()
        runner = PluginRunner(builder)
        runner.initialize()

        # Start for the first time with 'test' period
        runner.start_plugins()
        runner.stop_plugins('test')

        # Start again with the period
        runner.start_plugins()

        self.assertRaises(ValueError, runner.stop_plugins, 'test')
