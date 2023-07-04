import re
from typing import List

from hepbenchmarksuite.plugins.registry.timeseries_plugin import TimeseriesCollectorPlugin


class IpmiDcmiPowerConsumptionPlugin(TimeseriesCollectorPlugin):

    def __init__(self, interval_mins: float):
        super().__init__(interval_mins, unit='W')
        self.command = 'ipmitool dcmi power reading | grep "Instantaneous power reading:"'

    def collect_metric(self):
        # TODO: Implement collection of power consumption
        raise NotImplementedError("Will be implemented once we have a machine"
                                  " on which we can execute the command.")


class IpmiSdrElistPowerConsumptionPlugin(TimeseriesCollectorPlugin):

    def __init__(self, interval_mins: float, name_regex: str,
                 value_regex: str = r'(?P<value>\d+) Watts', command_arguments: str = ''):
        """
        Args:
            interval_mins: Determines how often the plugin runs
            name_regex: The result of the IPMI tool is searched for entries defined by this regex
            value_regex: Each found entry by the name_regex is is searched for this regex. It must contain a group.
            command_arguments: Additional arguments to the IPMI command
        """
        super().__init__(interval_mins, unit='W')
        self.name_regex = name_regex
        self.value_regex = value_regex
        self.command = f'ipmitool {command_arguments} sdr elist'

    def collect_metric(self):
        command_output = self.run_command(self.command)
        power_sources_consumption = self._parse(command_output)
        power_watts = sum(power_sources_consumption)
        return power_watts

    def _parse(self, command_output: str) -> List[int]:
        pattern = fr'{self.name_regex}.* {self.value_regex}'
        compiled_pattern = re.compile(pattern)

        matches = []
        for power in re.findall(compiled_pattern, command_output):
            matches.append(int(power))

        if len(matches) > 0:
            return matches
        else:
            raise RuntimeError(f"No power source found in the output of IPMI command ({self.command})."
                               f" Command output: {command_output}")
