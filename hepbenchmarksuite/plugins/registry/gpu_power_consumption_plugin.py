from hepbenchmarksuite.plugins.registry.timeseries_plugin import TimeseriesCollectorPlugin


class NvidiaSmiGPUPowerConsumptionPlugin(TimeseriesCollectorPlugin):

    def __init__(self, interval_mins: float):
        super().__init__(interval_mins, unit='W')
        self.command = "nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits | awk '{s+=$1} END {print s}'"

    def collect_metric(self):
        command_output = self.run_command(self.command)
        power_watts = float(command_output)
        power_watts = round(power_watts, 2)
        return power_watts
