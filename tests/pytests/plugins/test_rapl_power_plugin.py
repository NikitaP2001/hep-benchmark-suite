import unittest
from unittest.mock import MagicMock, patch

from hepbenchmarksuite.plugins.registry.rapl_power_plugin import RaplPowerPlugin, _EnergySelector


class TestEnergySelector(unittest.TestCase):

    def test_selector_falls_back_when_preferred_not_supported(self):
        pcap_reader = MagicMock()
        pcap_reader.is_supported.return_value = False

        perf_reader = MagicMock()
        perf_reader.is_supported.return_value = True

        msr_reader = MagicMock()
        msr_reader.is_supported.return_value = True

        with patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._PowercapReader', return_value=pcap_reader), \
             patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._PerfReader', return_value=perf_reader), \
             patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._MsrReader', return_value=msr_reader):
            selector = _EnergySelector(preferred_method='pcap')

        self.assertTrue(selector.is_supported())
        self.assertEqual('perf', selector.method)
        self.assertEqual(perf_reader, selector.reader)


class TestRaplPowerPlugin(unittest.TestCase):

    def test_on_start_sets_status_no_data_when_first_read_is_none(self):
        selector = MagicMock()
        selector.is_supported.return_value = True
        selector.method = 'pcap'
        selector.read_energy_j.return_value = None

        with patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._EnergySelector', return_value=selector):
            plugin = RaplPowerPlugin(interval_mins=0.5, preferred_method='pcap')
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertEqual('no_data', report['status'])
        self.assertEqual('pcap', report['method'])
        self.assertEqual([], report['values'])

    def test_execute_appends_power_sample(self):
        selector = MagicMock()
        selector.is_supported.return_value = True
        selector.method = 'msr'
        selector.read_energy_j.side_effect = [100.0, 130.0]

        with patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._EnergySelector', return_value=selector), \
             patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin.time.time', side_effect=[10.0, 20.0]):
            plugin = RaplPowerPlugin(interval_mins=0.5, preferred_method='msr')
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertEqual('ok', report['status'])
        self.assertEqual('msr', report['method'])
        self.assertEqual(1, len(report['values']))
        self.assertAlmostEqual(3.0, report['values'][0])

    def test_execute_skips_negative_energy_delta(self):
        selector = MagicMock()
        selector.is_supported.return_value = True
        selector.method = 'msr'
        selector.read_energy_j.side_effect = [200.0, 180.0]

        with patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._EnergySelector', return_value=selector), \
             patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin.time.time', side_effect=[10.0, 20.0]):
            plugin = RaplPowerPlugin(interval_mins=0.5, preferred_method='msr')
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertEqual([], report['values'])

    def test_on_end_closes_selector(self):
        selector = MagicMock()
        selector.is_supported.return_value = True
        selector.method = 'perf'
        selector.read_energy_j.return_value = 50.0

        with patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._EnergySelector', return_value=selector), \
             patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin.time.time', return_value=10.0):
            plugin = RaplPowerPlugin(interval_mins=0.5, preferred_method='perf')
            plugin.on_start()
            report = plugin.on_end()

        selector.close.assert_called_once()
        self.assertEqual('perf', report['method'])
        self.assertEqual('ok', report['status'])
