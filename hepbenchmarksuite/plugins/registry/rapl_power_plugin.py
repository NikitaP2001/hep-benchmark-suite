import ctypes
import os
import time
from typing import Optional

from hepbenchmarksuite.plugins.registry.timeseries_collector_plugin import TimeseriesCollectorPlugin


class _EnergyReader:
    def is_supported(self) -> bool:
        raise NotImplementedError()

    def read_energy_j(self) -> Optional[float]:
        raise NotImplementedError()

    def close(self) -> None:
        return


class _PowercapReader(_EnergyReader):
    _BASE_DIR = "/sys/class/powercap"
    _PREFIX = "intel-rapl:"

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.energy_paths = self._find_energy_paths()
        self._is_supported = self._test_read()

    def _find_energy_paths(self):
        if not os.path.isdir(self._BASE_DIR):
            return []
        paths = []
        for entry in os.listdir(self._BASE_DIR):
            if not entry.startswith(self._PREFIX):
                continue
            dir_path = os.path.join(self._BASE_DIR, entry)
            energy_path = os.path.join(dir_path, "energy_uj")
            if os.path.isfile(energy_path):
                paths.append(energy_path)
        return paths

    def _test_read(self) -> bool:
        if len(self.energy_paths) == 0:
            return False
        try:
            # Try reading once to validate access
            for path in self.energy_paths:
                with open(path, "r", encoding="utf-8") as handle:
                    int(handle.read().strip())
            return True
        except (OSError, ValueError):
            return False

    def is_supported(self) -> bool:
        return self._is_supported

    def read_energy_j(self) -> Optional[float]:
        total_uj = 0
        for path in self.energy_paths:
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    total_uj += int(handle.read().strip())
            except (OSError, ValueError):
                return None
        return total_uj / 1_000_000.0


class _MsrReader(_EnergyReader):
    _MSR_RAPL_POWER_UNIT = 0x606
    _MSR_PKG_ENERGY_STATUS = 0x611
    _MSR_FIELD_SIZE = 8

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.file_path = "/dev/cpu/0/msr"
        self.file = None
        self.energy_units = None
        try:
            self.file = open(self.file_path, "rb")
            pwr_unit = self._read_msr(self._MSR_RAPL_POWER_UNIT)
            esu_units = (pwr_unit >> 8) & 0x1F
            self.energy_units = pow(0.5, esu_units)
        except (OSError, IOError):
            self.file = None
            self.energy_units = None

    def is_supported(self) -> bool:
        return self.file is not None and self.energy_units is not None

    def _read_msr(self, offset: int) -> int:
        data = os.pread(self.file.fileno(), self._MSR_FIELD_SIZE, offset)
        return int.from_bytes(data, "little", signed=False)

    def read_energy_j(self) -> Optional[float]:
        if not self.is_supported():
            return None
        try:
            raw = self._read_msr(self._MSR_PKG_ENERGY_STATUS)
            return raw * self.energy_units
        except (OSError, IOError):
            return None

    def close(self) -> None:
        if self.file:
            self.file.close()


class _PerfEventAttr(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint),
        ("size", ctypes.c_uint),
        ("config", ctypes.c_ulong),
        ("sample_period_union", ctypes.c_ulong),
        ("sample_type", ctypes.c_ulong),
        ("read_format", ctypes.c_ulong),
        ("bitfields", ctypes.c_ulong),
        ("wakeup_events_union", ctypes.c_uint),
        ("bp_type", ctypes.c_uint),
        ("bp_addr_union", ctypes.c_ulong),
        ("bp_len_union", ctypes.c_ulong),
        ("branch_sample_type", ctypes.c_ulong),
        ("sample_regs_user", ctypes.c_ulong),
        ("sample_stack_user", ctypes.c_uint),
        ("clockid", ctypes.c_int),
        ("sample_regs_intr", ctypes.c_ulong),
        ("aux_watermark", ctypes.c_uint),
        ("sample_max_stack", ctypes.c_uint16),
        ("__reserved_2", ctypes.c_uint16),
        ("aux_sample_size", ctypes.c_uint),
        ("__reserved_3", ctypes.c_uint),
    ]

    def __init__(self):
        self.size = 120


class _PerfReader(_EnergyReader):
    _PERF_EVENT_OPEN = 298

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.fd = None
        self.scale = None
        self.perf_open = ctypes.CDLL(None).syscall
        self.perf_open.restype = ctypes.c_int
        self.perf_open.argtypes = (
            ctypes.c_long,
            ctypes.POINTER(_PerfEventAttr),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_ulong,
        )

        event_type = self._read_int("/sys/bus/event_source/devices/power/type")
        config = self._read_event_config("/sys/bus/event_source/devices/power/events/energy-pkg")
        self.scale = self._read_float("/sys/bus/event_source/devices/power/events/energy-pkg.scale")
        if event_type is None or config is None or self.scale is None:
            return

        attr = _PerfEventAttr()
        attr.type = event_type
        attr.config = config
        fd = self.perf_open(self._PERF_EVENT_OPEN, attr, -1, 0, -1, 0)
        if fd >= 0:
            self.fd = fd

    def is_supported(self) -> bool:
        return self.fd is not None and self.scale is not None

    def _read_int(self, path: str) -> Optional[int]:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return int(handle.read().strip())
        except (OSError, ValueError):
            return None

    def _read_float(self, path: str) -> Optional[float]:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return float(handle.read().strip())
        except (OSError, ValueError):
            return None

    def _read_event_config(self, path: str) -> Optional[int]:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                raw = handle.read().strip().split()[0]
            if "=" in raw:
                raw = raw.split("=")[1]
            return int(raw, 16)
        except (OSError, ValueError, IndexError):
            return None

    def read_energy_j(self) -> Optional[float]:
        if not self.is_supported():
            return None
        try:
            raw = int.from_bytes(os.read(self.fd, 8), "little", signed=False)
            return raw * self.scale
        except OSError:
            return None

    def close(self) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


class _EnergySelector:
    def __init__(self, preferred_method: Optional[str] = None, debug: bool = False):
        self.method = None
        self.reader = None
        self.debug = debug
        methods = {
            "pcap": _PowercapReader,
            "perf": _PerfReader,
            "msr": _MsrReader,
        }
        order = ["pcap", "perf", "msr"]
        if preferred_method in methods:
            order = [preferred_method] + [m for m in order if m != preferred_method]

        for name in order:
            reader = methods[name](debug)
            if reader.is_supported():
                self.method = name
                self.reader = reader
                break

    def is_supported(self) -> bool:
        return self.reader is not None

    def read_energy_j(self) -> Optional[float]:
        if not self.reader:
            return None
        return self.reader.read_energy_j()

    def close(self) -> None:
        if self.reader:
            self.reader.close()


class RaplPowerPlugin(TimeseriesCollectorPlugin):

    def __init__(self, interval_mins: float, preferred_method: Optional[str] = None, debug: bool = False):
        super().__init__("power-rapl", interval_mins, "W")
        self.preferred_method = preferred_method
        self.debug = debug
        self.selector = None
        self.selected_method = None
        self.status = "init"
        self.last_time = None
        self.last_energy = None

    def on_start(self) -> None:
        super().on_start()
        self.selector = _EnergySelector(self.preferred_method, self.debug)
        if not self.selector.is_supported():
            self.status = "unsupported"
            return
        self.selected_method = self.selector.method
        self.last_time = time.time()
        self.last_energy = self.selector.read_energy_j()
        self.status = "ok" if self.last_energy is not None else "no_data"

    def execute(self) -> None:
        if self.status != "ok":
            return
        now = time.time()
        energy = self.selector.read_energy_j() if self.selector else None
        if energy is None or self.last_energy is None or self.last_time is None:
            self.last_time = now
            self.last_energy = energy
            return

        dt = now - self.last_time
        if dt <= 0:
            self.last_time = now
            self.last_energy = energy
            return

        de = energy - self.last_energy
        if de < 0:
            self.last_time = now
            self.last_energy = energy
            return

        self.timeseries.append(de / dt)
        self.last_time = now
        self.last_energy = energy

    def on_end(self):
        if self.selector:
            self.selector.close()
        report = super().on_end()
        report["method"] = self.selected_method
        report["status"] = self.status
        return report