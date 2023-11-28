import datetime
import time
import unittest
from multiprocessing import Event
from unittest.mock import MagicMock

from hepbenchmarksuite.plugins.execution.strategy import ThreadExecutionStrategy
from hepbenchmarksuite.plugins.registry.command_executor import CommandExecutor


class TestCommandExecutor(unittest.TestCase):

    def setUp(self) -> None:
        metrics = self._get_config()
        self.executor = CommandExecutor(metrics)

    def _get_config(self):
        return {
            'foo': {
                'command': ' same_dummy',
                'regex': r'foo=(?P<value>\d+).*',
                'unit': '',
                'interval_mins': 5
            },
            'bar': {
                'command': 'same_dummy ',
                'regex': r'bar=(?P<value>\d+).*',
                'unit': '',
                'interval_mins': 1
            },
            'baz': {
                'command': 'same_dummy',
                'regex': r'baz=(?P<value>\d+).*',
                'unit': '',
                'interval_mins': 1
            }
        }

    def test_execute__executes_command_once(self):
        """
        If multiple metrics specify the same command, it is executed just once.
        """

        CommandExecutor.run_command = MagicMock(return_value="foo=1,bar=2,baz=4")

        self.executor.execute(list(self.executor.metrics.values()))

        CommandExecutor.run_command.assert_called_once()

        foo_value = self.executor.timeseries['foo'].get_last()
        self.assertEqual(1, foo_value)

        bar_value = self.executor.timeseries['bar'].get_last()
        self.assertEqual(2, bar_value)

        baz_value = self.executor.timeseries['baz'].get_last()
        self.assertEqual(4, baz_value)

    def test_on_end__produces_report_per_metric(self):
        """
        The report should be structured by the name of the metric first,
        under which the values and statistics are placed.
        """
        CommandExecutor.run_command = MagicMock(return_value="foo=1,bar=2,baz=4")

        self.executor.execute(list(self.executor.metrics.values()))

        report = self.executor.on_end()

        # Test all metrics are reported
        metric_names = list(report.keys())
        expected_metric_names = ['foo', 'bar', 'baz']
        self.assertListEqual(expected_metric_names, metric_names)

        # Test that the report contains values
        self.assertEqual(1, len(report['foo']['values']))
        self.assertEqual(1, len(report['bar']['values']))
        self.assertEqual(1, len(report['baz']['values']))

        # Test reported config section
        self.assertTrue('config' in report['foo'])
        foo_config = report['foo']['config']
        self.assertEqual('same_dummy', foo_config['command'])
        self.assertEqual(r'foo=(?P<value>\d+).*', foo_config['regex'])
        self.assertEqual('', foo_config['unit'])
        self.assertEqual('sum', foo_config['aggregation'])

    def test_determine_time_until_next_execution(self):
        """
        Tests that the two metrics with the same execution interval
        are to be executed next.
        """
        # 0.5 minute until group with the interval of 1 minute
        # 1.5 minute until group with the interval of 5 minutes
        time_now = datetime.datetime(2023, 1, 1, 0, 3, 30)
        start_time = datetime.datetime(2023, 1, 1, 0, 0, 0)
        time_until_next, metrics_to_execute = self.executor._determine_time_until_next_execution(start_time, time_now)

        self.assertAlmostEqual(30., time_until_next)
        print(metrics_to_execute)
        # There are two metrics--bar and baz--with the same time interval.
        self.assertEqual(2, len(metrics_to_execute))
        self.assertEqual(1, metrics_to_execute[0].interval_mins)
        self.assertEqual(1, metrics_to_execute[1].interval_mins)

    def test_determine_time_until_next_execution__floating_point_intervals(self):
        """
        Tests metrics with float intervals. Both metrics with the
        interval around 10 seconds will be round to exactly 10 seconds
        and collected together.
        """
        self.executor = CommandExecutor({
            'foo': {
                'command': '',
                'regex': '',
                'unit': '',
                'interval_mins': 0.1666999999  # 10.00200 seconds
            },
            'bar': {
                'command': '',
                'regex': '',
                'unit': '',
                'interval_mins': 0.1666666  # 9.999996 seconds
            },
            'baz': {
                'command': '',
                'regex': '',
                'unit': '',
                'interval_mins': 1
            }
        })
        start_time = datetime.datetime(2023, 1, 1, 0, 0, 0)
        time_now = datetime.datetime(2023, 1, 1, 0, 0, 0)
        time_until_next, metrics_to_execute = self.executor._determine_time_until_next_execution(start_time, time_now)

        self.assertAlmostEqual(self.executor.interval_granularity_secs, time_until_next)
        self.assertEqual(2, len(metrics_to_execute))
        expected_interval = self.executor.interval_granularity_secs / 60
        for metric in metrics_to_execute:
            self.assertEqual(expected_interval, metric.interval_mins)

    def test_determine_time_until_next_execution__multiple_groups(self):
        """
        Tests that even metrics with different intervals will
        be executed together next.
        """
        self.executor = CommandExecutor({
            'foo': {
                'command': '',
                'regex': '',
                'unit': '',
                'interval_mins': 1
            },
            'bar': {
                'command': '',
                'regex': '',
                'unit': '',
                'interval_mins': 2
            },
            'baz': {
                'command': '',
                'regex': '',
                'unit': '',
                'interval_mins': 5
            }
        })
        start_time = datetime.datetime(2023, 1, 1, 0, 0, 0)
        time_now = datetime.datetime(2023, 1, 1, 0, 3, 30)
        time_until_next, metrics_to_execute = self.executor._determine_time_until_next_execution(start_time, time_now)

        self.assertAlmostEqual(30., time_until_next)
        self.assertEqual(2, len(metrics_to_execute))
        intervals = {metric.interval_mins for metric in metrics_to_execute}
        self.assertSetEqual({1, 2}, intervals)

    def test_run(self):
        """
        Tests the whole command executor including command execution and
        report creation.
        """
        metrics = {
            'used-memory': {
                'command': 'free -m',
                'regex': r'Mem: *\d+ *(?P<value>\d+).*',
                'unit': 'MiB',
                'interval_mins': 0.00166666667  # 100 ms
            }
        }
        # Start the executor in a new thread to avoid hanging
        # on a wait inside the executor's run method.
        executor = CommandExecutor(metrics, interval_granularity_secs=0.1)
        stop_event = Event()
        execution_strategy = ThreadExecutionStrategy()
        execution_strategy.start(executor.start, args=(stop_event,))

        time.sleep(0.2)
        stop_event.set()
        execution_strategy.join()

        report = executor.get_result()

        self.assertListEqual(['used-memory', 'status'], list(report.keys()))
        self.assertTrue(len(report['used-memory']['values']) > 1)

    def test_plugin_resets_its_state(self):
        metrics = {
            'used-memory': {
                'command': 'free -m',
                'regex': r'Mem: *\d+ *(?P<value>\d+).*',
                'unit': 'MiB',
                'interval_mins': 0.00166666667  # 100 ms
            }
        }

        # Start the plugin for the first time and stop immediately
        plugin = CommandExecutor(metrics, interval_granularity_secs=0.1)
        stop_event = Event()
        execution_strategy = ThreadExecutionStrategy()
        execution_strategy.start(plugin.start, args=(stop_event,))
        stop_event.set()
        execution_strategy.join()

        result = plugin.get_result()
        self.assertEqual(1, len(result['used-memory']['values']))

        # Start the plugin for the second time and stop immediately
        stop_event = Event()
        execution_strategy.start(plugin.start, args=(stop_event,))
        stop_event.set()
        execution_strategy.join()

        # Should contain values of the second run only
        result = plugin.get_result()
        self.assertEqual(1, len(result['used-memory']['values']))
