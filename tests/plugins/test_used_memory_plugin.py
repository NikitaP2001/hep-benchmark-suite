import unittest
from unittest.mock import MagicMock

from hepbenchmarksuite.plugins.registry.used_memory_plugin import UsedMemoryPlugin


class TestUsedMemoryPlugin(unittest.TestCase):
    def test_collect_metric(self):
        command_output = """
              total        used        free      shared  buff/cache   available
Mem:          63791        1340       60798         182        1652       61616
Swap:         32223        1878       30345
        """

        plugin = UsedMemoryPlugin(interval_mins=1)
        plugin.run_command = MagicMock(return_value=command_output)

        used_memory_gib = plugin.collect_metric()

        plugin.run_command.assert_called_with(plugin.command)
        plugin.run_command.assert_called_once()
        self.assertAlmostEqual(1.31, used_memory_gib)
