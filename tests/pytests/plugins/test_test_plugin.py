import multiprocessing as mp
import time
import unittest
from typing import Dict

from hepbenchmarksuite.plugins.registry.test_plugin import TestPlugin


class TestTestPlugin(unittest.TestCase):

    def test_plugin(self):
        """
        Creates an instance of the TestPlugin and starts it
        in a new process. Lets it collect some measurements
        and then checks the results returned are correct.
        """
        event = mp.Event()
        plugin = TestPlugin()

        # Start the test plugin
        p = mp.Process(target=plugin.start, args=(event,))
        p.start()

        # Wait for the subprocess to collect some measurements
        time.sleep(1)

        # Signal the process to stop
        event.set()
        # Wait for the process to finish
        p.join()

        # Retrieve statistics
        result = plugin.get_result()

        # Check that the results from to the instance in the subprocesses are
        # returned here to the parent process.
        self.assertTrue(isinstance(result, Dict))
        self.assertListEqual(list(result.keys()), ['measurements', 'statistics', 'status'])
        count = list(result['measurements'].values())[0]
        self.assertTrue(count > 0)
