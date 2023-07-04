import unittest
from unittest.mock import MagicMock

from hepbenchmarksuite.plugins.registry.power_consumption_plugin import IpmiSdrElistPowerConsumptionPlugin


class TestIpmiSdrElistPowerConsumptionPlugin(unittest.TestCase):

    def test_collect_metric(self):
        with open('tests/plugins/command_outputs/ipmitool_sdr_elist', 'r') as file:
            command_output = file.read()

        plugin = IpmiSdrElistPowerConsumptionPlugin(
            interval_mins=1, name_regex=r'PS\d Power In')
        plugin.run_command = MagicMock(return_value=command_output)

        result = plugin.collect_metric()

        plugin.run_command.assert_called_with(plugin.command)
        plugin.run_command.assert_called_once()
        self.assertEqual(410, result)

    def test_collect_metric_2(self):
        with open('tests/plugins/command_outputs/ipmitool_sdr_elist_2', 'r') as file:
            command_output = file.read()

        plugin = IpmiSdrElistPowerConsumptionPlugin(
            interval_mins=1, name_regex=r'PS \d Output')
        plugin.run_command = MagicMock(return_value=command_output)

        result = plugin.collect_metric()

        plugin.run_command.assert_called_with(plugin.command)
        plugin.run_command.assert_called_once()
        self.assertEqual(110, result)
