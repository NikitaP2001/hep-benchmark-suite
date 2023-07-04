import re

from hepbenchmarksuite.plugins.registry.timeseries_plugin import TimeseriesCollectorPlugin


class UsedMemoryPlugin(TimeseriesCollectorPlugin):
    GIB_TO_MIB = 1024

    def __init__(self, interval_mins: float):
        super().__init__(interval_mins, unit='GiB')
        self.command = 'free -m'

    def collect_metric(self):
        command_output = self.run_command(self.command)
        mem_mib = self._parse(command_output)
        mem_gib = mem_mib / UsedMemoryPlugin.GIB_TO_MIB
        mem_gib = round(mem_gib, 2)
        return mem_gib

    def _parse(self, command_output: str) -> float:
        pattern = r'Mem: *(\d+) *(?P<value>\d+).*'
        match = re.search(pattern, command_output)
        if match:
            return int(match.group('value'))
        else:
            raise RuntimeError(f"Unable to extract value—unexpected command output: {command_output}")
