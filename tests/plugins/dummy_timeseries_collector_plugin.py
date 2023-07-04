from typing import Any

from hepbenchmarksuite.plugins.registry.timeseries_plugin import TimeseriesCollectorPlugin


class DummyTimeseriesCollectorPlugin(TimeseriesCollectorPlugin):

    def __init__(self, interval_mins: float):
        super().__init__(interval_mins, unit='dummy')
        self.counter = -1

    def collect_metric(self) -> Any:
        self.counter += 1
        return self.counter
