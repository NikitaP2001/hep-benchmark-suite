import re

from hepbenchmarksuite.plugins.registry.timeseries_plugin import TimeseriesCollectorPlugin


class CPUFrequencyPlugin(TimeseriesCollectorPlugin):
    GHZ_TO_HZ = 1_000_000

    def __init__(self, interval_mins: float):
        super().__init__(interval_mins, unit='GHz')
        self.command = 'cpupower frequency-info -f'

    def collect_metric(self):
        cmd_output = self.run_command(self.command)
        frequency_Hz = self._parse(cmd_output)
        frequency_GHz = frequency_Hz / CPUFrequencyPlugin.GHZ_TO_HZ
        frequency_GHz = round(frequency_GHz, 2)
        return frequency_GHz

    def _parse(self, command_output: str) -> int:
        pattern = r'current CPU frequency: (?P<value>\d+).*'
        match = re.search(pattern, command_output)
        if match:
            return int(match.group(1))
        else:
            raise RuntimeError(f"Unable to extract value—unexpected command output: {command_output}")
