import datetime
import time
import unittest
import math
from multiprocessing import Event
from unittest.mock import patch, MagicMock

from hepbenchmarksuite.plugins.execution.strategy import ThreadExecutionStrategy
from hepbenchmarksuite.plugins.registry.command_executor import CommandExecutor, BashCommandFailedException
from hepbenchmarksuite.utils import run_separated_commands

class TestCommandExecutorWithMixedCommands(unittest.TestCase):

    def setUp(self):
        """Common setup for each test."""
        self.call_count = 0  # Used to alternate between success and failure
        self.metrics = {
            'metric_success': {
                'command': 'dummy_command_success',
                'regex': r'value=(?P<value>\d+).*',
                'unit': '',
                'interval_mins': 0.2
            },
            'metric_fail': {
                'command': 'dummy_command_fail',
                'regex': r'value=(?P<value>\d+).*',
                'unit': '',
                'interval_mins': 0.2
            },
            'metric_sometimes_fails': {
                'command': 'dummy_command_sometimes_fails',
                'regex': r'value=(?P<value>\d+).*',
                'unit': '',
                'interval_mins': 0.1
            }
        }
        self.executor = CommandExecutor(self.metrics, interval_granularity_secs=1)

        # Patch run_separated_commands for all tests
        self.patcher = patch('hepbenchmarksuite.plugins.registry.command_executor.run_separated_commands')
        self.mock_run_separated_commands = self.patcher.start()

    def tearDown(self):
        """Cleanup after each test."""
        self.patcher.stop()  # Stop the mock patch

    def mock_run_command_side_effect(self, command):
        """Side effect to alternate between success and failure."""
        print(f'\n[mock_run_command_side_effect] command argument value is {command}')
        if command == 'dummy_command_success':
            return (0, 'value=42', '')  # Successful command
        elif command == 'dummy_command_fail':
            return (1, '', 'Command failed')  # Failed command

        # Alternate between success and failure for 'dummy_command_sometimes_fails'
        if command == 'dummy_command_sometimes_fails':
            self.call_count += 1
            if self.call_count % 2 == 1:
                print(f'[mock_run_command_side_effect]: call_count {self.call_count}, return success')
                return (0, 'value=42', '')  # Successful run
            else:
                print(f'[mock_run_command_side_effect]: call_count {self.call_count}, return fail')
                return (1, '', 'Command failed')  # Failed run

    def test_execute_with_one_failing_command(self):
        """
        Test that one command fails and the other succeeds, verifying that the 
        timeseries for the failed command receives NaN and the successful command 
        receives the parsed value.
        """
        # Set the side effect for mock_run_separated_commands
        self.mock_run_separated_commands.side_effect = self.mock_run_command_side_effect

        # Execute the commands
        self.executor.execute(list(self.executor.metrics.values()))

        # Check the successful metric value
        success_value = self.executor.timeseries['metric_success'].get_last()
        self.assertEqual(42, success_value)

        # Check the failing metric value, which should be NaN
        fail_value = self.executor.timeseries['metric_fail'].get_last()
        self.assertTrue(math.isnan(fail_value))

    def test_execute_with_alternating_success_and_failure(self):
        """
        Test that the command alternates between success and failure. 
        Ensure that the timeseries captures valid values and NaN for failures.
        """
        # Set the side effect for mock_run_separated_commands
        self.mock_run_separated_commands.side_effect = self.mock_run_command_side_effect

        # Set up execution strategy to run in a loop
        stop_event = Event()
        execution_strategy = ThreadExecutionStrategy()
        execution_strategy.start(self.executor.start, args=(stop_event,))

        # Let the executor run for 25 seconds to gather multiple data points
        time.sleep(25)
        stop_event.set()
        execution_strategy.join()

        # Now check the results for both metrics
        print("\nChecking 'metric_success' values:")
        timeseries_success = self.executor.timeseries['metric_success'].values
        print(f'metric_success values= {timeseries_success}')

        # Ensure that we have more than one value for 'metric_success'
        self.assertTrue(len(timeseries_success) > 1)
        print(f'passed check of len of timeseries_success')

        # Ensure that all values in 'metric_success' are 42 (no failures expected)
        for i, value in enumerate(timeseries_success.values()):
            print(f'value nr {i} in metric_success is {value}')
            self.assertEqual(value, 42)  # All values should be 42

        print("\nChecking 'metric_sometimes_fails' values:")
        timeseries_sometimes_fails = self.executor.timeseries['metric_sometimes_fails'].values
        print(f'metric_sometimes_fails values= {timeseries_sometimes_fails}')

        # Ensure that we have more than one value for 'metric_sometimes_fails'
        self.assertTrue(len(timeseries_sometimes_fails) > 1)
        print(f'passed check of len of timeseries_sometimes_fails')

        # Ensure that alternating values are either 42 or NaN
        for i, value in enumerate(timeseries_sometimes_fails.values()):
            print(f'value nr {i} in metric_sometimes_fails is {value}')
            if i % 2 == 0:
                # Even index should have value 42 (successful run)
                self.assertEqual(value, 42)
            else:
                # Odd index should have NaN (failed run)
                self.assertTrue(math.isnan(value))
