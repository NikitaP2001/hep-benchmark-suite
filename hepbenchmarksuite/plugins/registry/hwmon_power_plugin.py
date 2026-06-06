import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from hepbenchmarksuite.plugins.registry.timeseries_collector_plugin import TimeseriesCollectorPlugin

_HWMON_ROOT = Path("/sys/class/hwmon")

_DRIVER_MAP: List[Tuple[str, str]] = [
    ("scmi_sensors",     "ScmiSensorDevice"),
    ("a64fx_hwmon",      "A64fxDevice"),
    ("ipmi",             "IpmiDevice"),
    ("intel_rapl_mmio",  "RaplDevice"),
    ("intel_rapl",       "RaplDevice"),
    ("acpi_power_meter", "AcpiPowerDevice"),
]


def _read_int(path: Path) -> Optional[int]:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def _read_str(path: Path) -> Optional[str]:
    try:
        return path.read_text().strip()
    except OSError:
        return None


class HwmonDevice:
    """
    One /sys/class/hwmon/hwmonN directory.

    Reads power*_input (µW, instantaneous) and/or energy*_input (µJ,
    cumulative counter) from the sysfs tree.
    """

    def __init__(self, path: Path, driver: str):
        self.path = path
        self.driver = driver
        try:
            self._dev_path = path.resolve()
        except OSError:
            self._dev_path = path

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.path.name}, driver={self.driver!r})"

    def read_power_uw(self) -> Dict[str, int]:
        """Return {label: µW} for all power*_input files."""
        return self._read_indexed("power", "_input")

    def read_energy_uj(self) -> Dict[str, int]:
        """Return {label: µJ} for all energy*_input files."""
        return self._read_indexed("energy", "_input")

    def has_power_data(self) -> bool:
        try:
            p = self._dev_path
            return bool(list(p.glob("power*_input")) or list(p.glob("energy*_input")))
        except OSError:
            return False

    def energy_max_uj(self, label: str) -> int:
        """Return rollover limit for an energy domain (defaults to 2^32 µJ)."""
        for idx in range(64):
            if _read_str(self._dev_path / f"energy{idx}_label") == label:
                val = _read_int(self._dev_path / f"energy{idx}_max")
                return val if val else 2 ** 32
        val = _read_int(self._dev_path / "energy1_max")
        return val if val else 2 ** 32

    def _label(self, base: str, index: int) -> str:
        lbl = _read_str(self._dev_path / f"{base}{index}_label")
        return lbl if lbl else f"{base}{index}"

    def _read_indexed(self, prefix: str, suffix: str) -> Dict[str, int]:
        result: Dict[str, int] = {}
        try:
            for fpath in sorted(self._dev_path.glob(f"{prefix}*{suffix}")):
                try:
                    idx = int("".join(filter(str.isdigit, fpath.name.split("_")[0])))
                except ValueError:
                    idx = 0
                val = _read_int(fpath)
                if val is not None:
                    result[self._label(prefix, idx)] = val
        except OSError:
            pass
        return result


class ScmiSensorDevice(HwmonDevice):
    """Arm SCMI firmware sensor interface (scmi_sensors driver)."""


class A64fxDevice(HwmonDevice):
    """Fujitsu A64FX CMG power sensors (a64fx_hwmon driver)."""


class IpmiDevice(HwmonDevice):
    """IPMI/BMC sensor bridge (ipmi driver)."""


class RaplDevice(HwmonDevice):
    """
    Intel RAPL counters (intel_rapl_mmio / intel_rapl drivers).

    Exposes energy*_input (µJ cumulative); power*_input is absent.
    """

    def read_power_uw(self) -> Dict[str, int]:
        return {}


class AcpiPowerDevice(HwmonDevice):
    """ACPI whole-system power meter (acpi_power_meter driver)."""


class GenericHwmonDevice(HwmonDevice):
    """Fallback for any hwmon device that exposes power or energy sysfs files."""


_CLASS_BY_DRIVER: Dict[str, type] = {
    drv: globals()[cls] for drv, cls in _DRIVER_MAP
}


class HwmonScanner:
    """Enumerates /sys/class/hwmon/ and returns HwmonDevice objects."""

    @staticmethod
    def scan(hwmon_root: Path = _HWMON_ROOT) -> List[HwmonDevice]:
        """Return one HwmonDevice per discovered power/energy-capable hwmon directory."""
        devices: List[HwmonDevice] = []
        if not hwmon_root.exists():
            return devices
        try:
            entries = list(hwmon_root.iterdir())
        except OSError:
            return devices
        for entry in sorted(entries):
            try:
                driver = None
                for nc in (entry / "name", entry.resolve() / "name"):
                    driver = _read_str(nc)
                    if driver:
                        break
                if not driver:
                    continue
                cls = _CLASS_BY_DRIVER.get(driver, GenericHwmonDevice)
                dev = cls(entry, driver)
                if dev.has_power_data():
                    devices.append(dev)
            except OSError:
                continue
        return devices


class HwmonPowerPlugin(TimeseriesCollectorPlugin):
    """
    Collects instantaneous CPU/SoC power (W) via Linux hwmon sysfs.

    """

    def __init__(
        self,
        interval_mins: float,
        hwmon_root: Optional[Path] = None,
        debug: bool = False,
    ):
        super().__init__("power-hwmon", interval_mins, "W")
        self._hwmon_root = hwmon_root or _HWMON_ROOT
        self.debug = debug
        self.devices: List[HwmonDevice] = []
        self.domains: List[str] = []
        self.selected_method: Optional[str] = None
        self.status = "init"
        self._last_energy: Dict[str, Dict[str, int]] = {}
        self._last_time: Optional[float] = None

    def on_start(self) -> None:
        super().on_start()
        self.devices = HwmonScanner.scan(self._hwmon_root)
        if not self.devices:
            self.status = "unsupported"
            return

        has_power = False
        has_energy = False
        domains: List[str] = []

        for dev in self.devices:
            try:
                for label in dev.read_power_uw():
                    domains.append(f"{repr(dev)}/{label}")
                    has_power = True
                energy = dev.read_energy_uj()
                for label in energy:
                    domains.append(f"{repr(dev)}/{label}")
                    has_energy = True
                if energy:
                    self._last_energy[repr(dev)] = dict(energy)
            except OSError:
                continue

        if not domains:
            self.status = "no_data"
            return

        self.domains = domains
        self.selected_method = (
            "mixed"  if (has_power and has_energy) else
            "energy" if has_energy                 else
            "power"
        )
        self._last_time = time.time()
        self.status = "ok"

    def execute(self) -> None:
        if self.status != "ok":
            return
        now = time.time()
        dt = now - self._last_time
        if dt <= 0:
            self._last_time = now
            return

        total_w = 0.0
        any_reading = False

        for dev in self.devices:
            try:
                # Strategy 1: instantaneous power*_input (µW -> W)
                for uw in dev.read_power_uw().values():
                    total_w += uw / 1_000_000.0
                    any_reading = True

                # Strategy 2: energy*_input counter delta (µJ Δ / Δt -> W)
                energy = dev.read_energy_uj()
                if energy:
                    prev = self._last_energy.get(repr(dev), {})
                    for label, uj in energy.items():
                        prev_uj = prev.get(label, uj)
                        delta_uj = uj - prev_uj
                        if delta_uj < 0:
                            delta_uj += dev.energy_max_uj(label)
                        total_w += (delta_uj / 1_000_000.0) / dt
                        any_reading = True
                    self._last_energy[repr(dev)] = dict(energy)
            except OSError:
                continue

        if any_reading:
            self.timeseries.append(total_w)
            self._last_time = now

    def on_end(self) -> dict:
        report = super().on_end()
        report["method"] = self.selected_method
        report["status"] = self.status
        report["domains"] = self.domains
        return report
