"""CPU frequency plugin module."""

import os
from statistics import mean

from hepbenchmarksuite.plugins.registry.timeseries_collector_plugin import TimeseriesCollectorPlugin


class CPUFrequencyPlugin(TimeseriesCollectorPlugin):
    """This timeseries plugin reports the CPU frequenzy in kHz periodically."""

    def __init__(self, interval_mins: float):
        super().__init__('cpu-frequency', interval_mins, 'kHz')
        
        cpu_base_path = '/sys/devices/system/cpu/'
        self.cpu_directories = [
            d for d in os.listdir(cpu_base_path) if d.startswith('cpu') and d[3:].isdigit()
        ]

        if len(self.cpu_directories) == 0:
            raise RuntimeError('No CPUs found in /sys/devices/system/cpu/')

    def execute(self) -> None:
        """
        Collects the current CPU frequencies and appends them to the timeseries data.
        """
        frequencies = []
        for cpu_dir in self.cpu_directories:
            freq_path = f'/sys/devices/system/cpu/{cpu_dir}/cpufreq/scaling_cur_freq'
            try:
                with open(freq_path, 'r', encoding='utf-8') as freq_file:
                    scaling_cur_freq = int(freq_file.read().strip())
                frequencies.append(scaling_cur_freq)
            except FileNotFoundError:
                print(f"Warning: {freq_path} not found.")
            except ValueError:
                print(f"Warning: Invalid value in {freq_path}.")
            except PermissionError:
                print(f"Warning: Permission denied accessing {freq_path}.")

        if frequencies:
            self.timeseries.append(mean(frequencies))
        else:
            print("Warning: No CPU frequencies were appended due to earlier errors.")
