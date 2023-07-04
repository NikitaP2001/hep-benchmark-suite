import unittest
from unittest.mock import MagicMock

from hepbenchmarksuite.plugins.registry.cpu_frequency_plugin import CPUFrequencyPlugin


class TestCPUFrequencyPlugin(unittest.TestCase):

    def setUp(self) -> None:
        self.command_output = """
analyzing CPU 0:
  current CPU frequency: 1384722 (asserted by call to kernel)
        """

    def test_collect_metric(self):
        plugin = CPUFrequencyPlugin(interval_mins=1)
        plugin.run_command = MagicMock(return_value=self.command_output)

        frequency_ghz = plugin.collect_metric()

        plugin.run_command.assert_called_with(plugin.command)
        plugin.run_command.assert_called_once()
        self.assertAlmostEqual(1.38, frequency_ghz)
