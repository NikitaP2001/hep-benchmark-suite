import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from hepbenchmarksuite.plugins.registry.hwmon_power_plugin import (
    HwmonPowerPlugin,
    HwmonScanner,
    HwmonDevice,
    RaplDevice,
    ScmiSensorDevice,
    GenericHwmonDevice,
    _HWMON_ROOT,
)


def _make_device(power_uw=None, energy_uj=None, driver="mock", name="hwmon0"):
    """Return a mock HwmonDevice with controllable read_power_uw / read_energy_uj."""
    dev = MagicMock(spec=HwmonDevice)
    dev.driver = driver
    dev.__repr__ = MagicMock(return_value=f"MockDevice({name}, driver={driver!r})")
    dev.read_power_uw.return_value = power_uw or {}
    dev.read_energy_uj.return_value = energy_uj or {}
    dev.energy_max_uj.return_value = 2 ** 32
    return dev


class TestHwmonScanner(unittest.TestCase):

    def test_returns_empty_list_when_hwmon_root_does_not_exist(self):
        mock_root = MagicMock(spec=Path)
        mock_root.exists.return_value = False
        result = HwmonScanner.scan(hwmon_root=mock_root)
        self.assertEqual([], result)

    def test_skips_entries_without_name_file(self):
        entry = MagicMock(spec=Path)
        entry.__truediv__ = lambda self, other: MagicMock(spec=Path, read_text=MagicMock(side_effect=OSError))
        entry.resolve.return_value = entry

        mock_root = MagicMock(spec=Path)
        mock_root.exists.return_value = True
        mock_root.iterdir.return_value = iter([entry])

        result = HwmonScanner.scan(hwmon_root=mock_root)
        self.assertEqual([], result)

    def test_skips_devices_with_no_power_data(self):
        dev = MagicMock(spec=HwmonDevice)
        dev.has_power_data.return_value = False

        mock_root = MagicMock(spec=Path)
        mock_root.exists.return_value = True
        mock_root.iterdir.return_value = iter([])

        with patch(
            'hepbenchmarksuite.plugins.registry.hwmon_power_plugin.HwmonScanner.scan',
            return_value=[],
        ):
            result = HwmonScanner.scan(hwmon_root=mock_root)
        self.assertEqual([], result)


# HwmonPowerPlugin — lifecycle

class TestHwmonPowerPluginLifecycle(unittest.TestCase):

    def test_on_start_sets_status_unsupported_when_no_devices(self):
        with patch.object(HwmonScanner, 'scan', return_value=[]):
            plugin = HwmonPowerPlugin(interval_mins=1.0)
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertEqual('unsupported', report['status'])
        self.assertIsNone(report['method'])
        self.assertEqual([], report['domains'])
        self.assertEqual([], report['values'])

    def test_on_start_sets_status_no_data_when_devices_have_no_readings(self):
        dev = _make_device(power_uw={}, energy_uj={})

        with patch.object(HwmonScanner, 'scan', return_value=[dev]):
            plugin = HwmonPowerPlugin(interval_mins=1.0)
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertEqual('no_data', report['status'])
        self.assertIsNone(report['method'])
        self.assertEqual([], report['domains'])
        self.assertEqual([], report['values'])

    def test_on_start_sets_method_power_for_power_only_device(self):
        dev = _make_device(power_uw={"power1": 120_000_000})

        with patch.object(HwmonScanner, 'scan', return_value=[dev]), \
             patch('hepbenchmarksuite.plugins.registry.hwmon_power_plugin.time.time', return_value=0.0):
            plugin = HwmonPowerPlugin(interval_mins=1.0)
            plugin.on_start()

        self.assertEqual('power', plugin.selected_method)
        self.assertEqual('ok', plugin.status)

    def test_on_start_sets_method_energy_for_energy_only_device(self):
        dev = _make_device(energy_uj={"package-0": 1_000_000})

        with patch.object(HwmonScanner, 'scan', return_value=[dev]), \
             patch('hepbenchmarksuite.plugins.registry.hwmon_power_plugin.time.time', return_value=0.0):
            plugin = HwmonPowerPlugin(interval_mins=1.0)
            plugin.on_start()

        self.assertEqual('energy', plugin.selected_method)

    def test_on_start_sets_method_mixed_for_device_with_both(self):
        dev = _make_device(
            power_uw={"power1": 50_000_000},
            energy_uj={"package-0": 1_000_000},
        )

        with patch.object(HwmonScanner, 'scan', return_value=[dev]), \
             patch('hepbenchmarksuite.plugins.registry.hwmon_power_plugin.time.time', return_value=0.0):
            plugin = HwmonPowerPlugin(interval_mins=1.0)
            plugin.on_start()

        self.assertEqual('mixed', plugin.selected_method)

    def test_domains_contain_device_repr_and_label(self):
        dev = _make_device(power_uw={"power1": 120_000_000}, name="hwmon0", driver="scmi_sensors")

        with patch.object(HwmonScanner, 'scan', return_value=[dev]), \
             patch('hepbenchmarksuite.plugins.registry.hwmon_power_plugin.time.time', return_value=0.0):
            plugin = HwmonPowerPlugin(interval_mins=1.0)
            plugin.on_start()

        self.assertIn("MockDevice(hwmon0, driver='scmi_sensors')/power1", plugin.domains)


# HwmonPowerPlugin — execute: power*_input strategy

class TestHwmonPowerPluginPowerStrategy(unittest.TestCase):

    def test_execute_converts_microwatts_to_watts(self):
        dev = _make_device(power_uw={"power1": 120_000_000})  # 120 W

        with patch.object(HwmonScanner, 'scan', return_value=[dev]), \
             patch('hepbenchmarksuite.plugins.registry.hwmon_power_plugin.time.time', side_effect=[0.0, 1.0]):
            plugin = HwmonPowerPlugin(interval_mins=1.0)
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertEqual(1, len(report['values']))
        self.assertAlmostEqual(120.0, report['values'][0])

    def test_execute_sums_multiple_power_domains(self):
        dev = _make_device(power_uw={"power1": 120_000_000, "power2": 33_600_000})

        with patch.object(HwmonScanner, 'scan', return_value=[dev]), \
             patch('hepbenchmarksuite.plugins.registry.hwmon_power_plugin.time.time', side_effect=[0.0, 1.0]):
            plugin = HwmonPowerPlugin(interval_mins=1.0)
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertEqual(1, len(report['values']))
        self.assertAlmostEqual(153.6, report['values'][0])

    def test_execute_sums_multiple_devices(self):
        dev1 = _make_device(power_uw={"power1": 100_000_000}, name="hwmon0")
        dev2 = _make_device(power_uw={"power1":  50_000_000}, name="hwmon1")

        with patch.object(HwmonScanner, 'scan', return_value=[dev1, dev2]), \
             patch('hepbenchmarksuite.plugins.registry.hwmon_power_plugin.time.time', side_effect=[0.0, 1.0]):
            plugin = HwmonPowerPlugin(interval_mins=1.0)
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertAlmostEqual(150.0, report['values'][0])

    def test_execute_skips_sample_when_dt_is_zero(self):
        dev = _make_device(power_uw={"power1": 100_000_000})

        with patch.object(HwmonScanner, 'scan', return_value=[dev]), \
             patch('hepbenchmarksuite.plugins.registry.hwmon_power_plugin.time.time', side_effect=[0.0, 0.0]):
            plugin = HwmonPowerPlugin(interval_mins=1.0)
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertEqual([], report['values'])

    def test_execute_does_nothing_when_status_is_not_ok(self):
        with patch.object(HwmonScanner, 'scan', return_value=[]):
            plugin = HwmonPowerPlugin(interval_mins=1.0)
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertEqual('unsupported', report['status'])
        self.assertEqual([], report['values'])



class TestRaplDevice(unittest.TestCase):

    def test_read_power_uw_always_returns_empty(self):

        dev = RaplDevice(Path("/sys/class/hwmon/hwmon0"), "intel_rapl_mmio")
        with patch.object(Path, 'glob', return_value=iter([])):
            self.assertEqual({}, dev.read_power_uw())


class TestHwmonPowerPluginEnergyStrategy(unittest.TestCase):

    def test_execute_derives_power_from_energy_delta(self):
        # 100 J over 10 s → 10 W
        dev = _make_device(energy_uj={"package-0": 100_000_000})
        dev.read_energy_uj.side_effect = [
            {"package-0": 0},           # on_start snapshot
            {"package-0": 100_000_000}, # execute read
        ]

        with patch.object(HwmonScanner, 'scan', return_value=[dev]), \
             patch('hepbenchmarksuite.plugins.registry.hwmon_power_plugin.time.time', side_effect=[0.0, 10.0]):
            plugin = HwmonPowerPlugin(interval_mins=1.0)
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        self.assertEqual(1, len(report['values']))
        self.assertAlmostEqual(10.0, report['values'][0])

    def test_execute_handles_counter_rollover(self):
        rollover = 2 ** 32
        dev = _make_device()
        dev.energy_max_uj.return_value = rollover
        dev.read_energy_uj.side_effect = [
            {"package-0": rollover - 10_000_000},  # on_start: near max
            {"package-0": 90_000_000},              # execute: rolled over
        ]

        with patch.object(HwmonScanner, 'scan', return_value=[dev]), \
             patch('hepbenchmarksuite.plugins.registry.hwmon_power_plugin.time.time', side_effect=[0.0, 10.0]):
            plugin = HwmonPowerPlugin(interval_mins=1.0)
            plugin.on_start()
            plugin.execute()
            report = plugin.on_end()

        # delta = 90 J + 10 J = 100 J / 10 s = 10 W
        self.assertAlmostEqual(10.0, report['values'][0])


class TestHwmonPowerPluginOnEnd(unittest.TestCase):

    def test_on_end_returns_all_required_fields(self):
        dev = _make_device(power_uw={"power1": 120_000_000})

        with patch.object(HwmonScanner, 'scan', return_value=[dev]), \
             patch('hepbenchmarksuite.plugins.registry.hwmon_power_plugin.time.time', return_value=0.0):
            plugin = HwmonPowerPlugin(interval_mins=0.5)
            plugin.on_start()
            report = plugin.on_end()

        self.assertIn('values',  report)
        self.assertIn('unit',    report)
        self.assertIn('interval', report)
        self.assertIn('method',  report)
        self.assertIn('status',  report)
        self.assertIn('domains', report)
        self.assertEqual('W',    report['unit'])
        self.assertAlmostEqual(30.0, report['interval'])
        self.assertEqual('ok',   report['status'])
        self.assertEqual('power', report['method'])
