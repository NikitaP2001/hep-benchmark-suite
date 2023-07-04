import unittest
from unittest.mock import MagicMock

from hepbenchmarksuite.plugins.registry.gpu_power_consumption_plugin import NvidiaSmiGPUPowerConsumptionPlugin


class TestGPUPowerConsumptionPlugin(unittest.TestCase):
    def test_collect_metric(self):
        command_output = '7.98\n'
        plugin = NvidiaSmiGPUPowerConsumptionPlugin(interval_mins=1)
        plugin.run_command = MagicMock(return_value=command_output)

        power_watts = plugin.collect_metric()

        plugin.run_command.assert_called_with(plugin.command)
        plugin.run_command.assert_called_once()
        self.assertEqual(7.98, power_watts)
