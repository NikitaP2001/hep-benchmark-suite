import multiprocessing as mp
import subprocess
import time
import unittest
from typing import List

from hepbenchmarksuite.plugins.execution.strategy import ExecutionStrategy, ThreadExecutionStrategy, \
    ProcessExecutionStrategy
from tests.plugins.dummy_timeseries_plugin import DummyTimeseriesPlugin


def measure_time(function) -> float:
    """
    Measures the time it takes to execute the given function
    in seconds.
    """
    time_before = time.time()
    function()
    time_after = time.time()
    time_taken = time_after - time_before
    return time_taken


def get_thread_pids_of_process(pid: int) -> List[int]:
    # run the "ps" command to get information about the process and its threads
    process_info = subprocess.check_output(["ps", "-T", "-p", str(pid)])
    # split the output into lines
    lines = process_info.decode().strip().split("\n")
    # skip the header line
    thread_lines = lines[1:]
    # parse the thread IDs from each line of output
    thread_pids = [int(line.split()[0]) for line in thread_lines]
    return thread_pids


class TestTimeseriesCollectorPlugin(unittest.TestCase):

    def start_new_plugin(self, interval_secs: float, execution_strategy: ExecutionStrategy):
        interval_mins = interval_secs / 60
        self.plugin = DummyTimeseriesPlugin(interval_mins)
        self.event = mp.Event()
        execution_strategy.start(self.plugin.start, args=(self.event,))
        # self.start_plugin(self.plugin)

    def test_plugin_ends_immediately_on_signal(self):
        """
        The plugin should be cancelled immediately upon signalling
        (as opposed to waiting until the next period finishes).
        """
        # Set a large interval so that the plugin will be idle during
        # the requested cancellation.
        strategy = ThreadExecutionStrategy()
        self.start_new_plugin(interval_secs=60, execution_strategy=strategy)
        thread = strategy.thread

        def stop_plugin():
            # Signal the process to stop immediately
            self.event.set()
            # Wait for the process to finish
            strategy.join()

        time_taken = measure_time(stop_plugin)

        # Test the process has finished.
        self.assertFalse(thread.is_alive())

        # The time it takes to cancel the process should take very little time.
        max_time_until_cancellation_secs = 0.02
        self.assertLess(time_taken, max_time_until_cancellation_secs)

    def test_plugin_is_single_threaded(self):
        """
        Checks that the number of threads created by a process
        does not change during the execution of the plugin.
        """
        strategy = ProcessExecutionStrategy()
        self.start_new_plugin(interval_secs=0.05, execution_strategy=strategy)

        threads_before = get_thread_pids_of_process(strategy.process.pid)
        # Let the process work for a second
        time.sleep(1)
        threads_after = get_thread_pids_of_process(strategy.process.pid)

        strategy.process.terminate()

        self.assertEqual(len(threads_before), len(threads_after))

    def test_collected_metrics(self):
        """
        Tests that the plugin collected some metrics and that
        the individual measurements are sorted in the order
        in which they were collected.
        """
        interval_secs = 0.01
        strategy = ThreadExecutionStrategy()
        self.start_new_plugin(interval_secs=interval_secs, execution_strategy=strategy)

        # Let the process work a little.
        time.sleep(0.5)

        self.event.set()
        strategy.join()

        result = self.plugin.get_result()
        measurements = result['values']

        # Should have produced something
        self.assertTrue(len(measurements) > 0)

        def is_ordered(values):
            return all(values[i] <= values[i + 1] for i in range(len(values) - 1))

        # The collected data should be ordered
        values = list(measurements)
        values_sorted = is_ordered(values)
        self.assertTrue(values_sorted)

        # Should contain timestamps and start_time < end_time
        start_time = result['start_time']
        end_time = result['end_time']
        self.assertLessEqual(start_time, end_time, "The start should come before the end.")

        unit = result['unit']
        self.assertEqual('unit', unit)

        interval = result['interval']
        self.assertAlmostEqual(interval_secs, interval)

    def test_plugin_is_run_on_startup(self):
        strategy = ThreadExecutionStrategy()
        self.start_new_plugin(interval_secs=2, execution_strategy=strategy)

        # Let the process work a little.
        time.sleep(0.3)

        # And stop before the timer goes off for the first time
        self.event.set()
        strategy.join()

        result = self.plugin.get_result()
        measurements = result['values']

        # Should contain a single measurement
        self.assertEqual(1, len(measurements))

    def test_plugin_resets_its_state(self):
        # Start the plugin for the first time and stop immediately
        strategy = ThreadExecutionStrategy()
        self.start_new_plugin(interval_secs=60, execution_strategy=strategy)
        self.event.set()
        strategy.join()

        result = self.plugin.get_result()
        self.assertEqual(1, len(result['values']))

        # Start the plugin for the second time and stop immediately
        self.event = mp.Event()
        strategy.start(self.plugin.start, args=(self.event,))
        self.event.set()
        strategy.join()

        # Should contain values of the second run only
        result = self.plugin.get_result()
        self.assertEqual(1, len(result['values']))
