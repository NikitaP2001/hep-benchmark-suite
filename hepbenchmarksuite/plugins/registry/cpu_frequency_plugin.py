import os
from statistics import mean

from hepbenchmarksuite.plugins.registry.timeseries_collector_plugin import TimeseriesCollectorPlugin


class CPUFrequencyPlugin(TimeseriesCollectorPlugin):

    def __init__(self, interval_mins: float):
        super().__init__('cpu-frequency', interval_mins, 'kHz')

        self.cpu_directories = [d for d in os.listdir('/sys/devices/system/cpu/') if
                                d.startswith('cpu') and d[3:].isdigit()]

        if len(self.cpu_directories) == 0:
            raise RuntimeError('No CPUs found in /sys/devices/system/cpu/')

    def execute(self) -> None:
        frequencies = []
        for cpu_dir in self.cpu_directories:
            freq_path = f'/sys/devices/system/cpu/{cpu_dir}/cpufreq/scaling_cur_freq'

            with open(freq_path, 'r') as freq_file:
                scaling_cur_freq = int(freq_file.read().strip())

            frequencies.append(scaling_cur_freq)

        frequency = int(mean(frequencies))
        self.timeseries.append(frequency)
