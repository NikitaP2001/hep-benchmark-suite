import unittest
from unittest.mock import MagicMock, patch

from hepbenchmarksuite.plugins.registry.rapl_power_plugin import RaplPowerPlugin, _EnergySelector, _PowercapReader


class TestEnergySelector(unittest.TestCase):

    def test_selector_uses_default_order_when_preferred_not_specified(self):
        pcap_reader = MagicMock()
        pcap_reader.is_supported.return_value = True

        perf_reader = MagicMock()
        perf_reader.is_supported.return_value = True

        msr_reader = MagicMock()
        msr_reader.is_supported.return_value = True

        with patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._PowercapReader', return_value=pcap_reader), \
             patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._PerfReader', return_value=perf_reader), \
             patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._MsrReader', return_value=msr_reader):
            selector = _EnergySelector(preferred_method=None)

        self.assertTrue(selector.is_supported())
        self.assertEqual('pcap', selector.method)
        self.assertEqual(pcap_reader, selector.reader)

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

    def test_selector_reports_unsupported_when_no_method_is_available(self):
        pcap_reader = MagicMock()
        pcap_reader.is_supported.return_value = False

        perf_reader = MagicMock()
        perf_reader.is_supported.return_value = False

        msr_reader = MagicMock()
        msr_reader.is_supported.return_value = False

        with patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._PowercapReader', return_value=pcap_reader), \
             patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._PerfReader', return_value=perf_reader), \
             patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._MsrReader', return_value=msr_reader):
            selector = _EnergySelector(preferred_method=None)

        self.assertFalse(selector.is_supported())
        self.assertIsNone(selector.method)
        self.assertIsNone(selector.reader)


class TestPowercapReader(unittest.TestCase):

    def test_prefers_package_domains_over_other_top_level_domains(self):
        entries = ["intel-rapl:0", "intel-rapl:1", "intel-rapl:0:0", "intel-rapl-mmio:0"]

        def mock_isdir(path):
            if path == _PowercapReader._BASE_DIR:
                return True
            return path in [
                f"{_PowercapReader._BASE_DIR}/intel-rapl:0",
                f"{_PowercapReader._BASE_DIR}/intel-rapl:1",
                f"{_PowercapReader._BASE_DIR}/intel-rapl:0:0",
            ]

        def mock_isfile(path):
            return path in [
                f"{_PowercapReader._BASE_DIR}/intel-rapl:0/energy_uj",
                f"{_PowercapReader._BASE_DIR}/intel-rapl:1/energy_uj",
            ]

        def mock_zone_name(_self, dir_path):
            mapping = {
                f"{_PowercapReader._BASE_DIR}/intel-rapl:0": "package-0",
                f"{_PowercapReader._BASE_DIR}/intel-rapl:1": "dram",
            }
            return mapping.get(dir_path, "")

        with patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin.os.path.isdir', side_effect=mock_isdir), \
             patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin.os.listdir', return_value=entries), \
             patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin.os.path.isfile', side_effect=mock_isfile), \
             patch.object(_PowercapReader, '_read_zone_name', new=mock_zone_name), \
             patch.object(_PowercapReader, '_test_read', return_value=True):
            reader = _PowercapReader(debug=False)

        self.assertEqual(['package-0'], reader.selected_domains)
        self.assertEqual([f"{_PowercapReader._BASE_DIR}/intel-rapl:0/energy_uj"], reader.energy_paths)


class TestRaplPowerPlugin(unittest.TestCase):

    def test_on_start_sets_status_unsupported_when_selector_not_supported(self):
        selector = MagicMock()
        selector.is_supported.return_value = False

        with patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._EnergySelector', return_value=selector):
            plugin = RaplPowerPlugin(interval_mins=0.5, preferred_method='pcap')
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertEqual('unsupported', report['status'])
        self.assertIsNone(report['method'])
        self.assertEqual([], report['domains'])
        self.assertEqual([], report['values'])

    def test_on_start_sets_status_no_data_when_first_read_is_none(self):
        selector = MagicMock()
        selector.is_supported.return_value = True
        selector.method = 'pcap'
        selector.read_energy_j.return_value = None
        selector.selected_domains.return_value = ['package-0']

        with patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._EnergySelector', return_value=selector):
            plugin = RaplPowerPlugin(interval_mins=0.5, preferred_method='pcap')
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertEqual('no_data', report['status'])
        self.assertEqual('pcap', report['method'])
        self.assertEqual(['package-0'], report['domains'])
        self.assertEqual([], report['values'])

    def test_execute_appends_power_sample(self):
        selector = MagicMock()
        selector.is_supported.return_value = True
        selector.method = 'msr'
        selector.read_energy_j.side_effect = [100.0, 130.0]
        selector.selected_domains.return_value = []

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

    def test_execute_ignores_nonpositive_time_or_negative_energy_delta(self):
        selector = MagicMock()
        selector.is_supported.return_value = True
        selector.method = 'msr'
        selector.read_energy_j.side_effect = [100.0, 120.0]
        selector.selected_domains.return_value = []

        with patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._EnergySelector', return_value=selector), \
             patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin.time.time', side_effect=[10.0, 10.0]):
            plugin = RaplPowerPlugin(interval_mins=0.5, preferred_method='msr')
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertEqual([], report['values'])

        selector = MagicMock()
        selector.is_supported.return_value = True
        selector.method = 'msr'
        selector.read_energy_j.side_effect = [200.0, 180.0]
        selector.selected_domains.return_value = []

        with patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._EnergySelector', return_value=selector), \
             patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin.time.time', side_effect=[10.0, 20.0]):
            plugin = RaplPowerPlugin(interval_mins=0.5, preferred_method='msr')
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertEqual([], report['values'])

    def test_on_end_closes_selector_and_returns_plugin_fields(self):
        selector = MagicMock()
        selector.is_supported.return_value = True
        selector.method = 'perf'
        selector.read_energy_j.return_value = 50.0
        selector.selected_domains.return_value = ['package-0']

        with patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin._EnergySelector', return_value=selector), \
             patch('hepbenchmarksuite.plugins.registry.rapl_power_plugin.time.time', return_value=10.0):
            plugin = RaplPowerPlugin(interval_mins=0.5, preferred_method='perf')
            plugin.on_start()
            report = plugin.on_end()

        selector.close.assert_called_once()
        self.assertEqual('perf', report['method'])
        self.assertEqual('ok', report['status'])
        self.assertEqual(['package-0'], report['domains'])
        self.assertEqual('W', report['unit'])
        self.assertAlmostEqual(30.0, report['interval'])
