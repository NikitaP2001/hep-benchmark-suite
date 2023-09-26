from abc import ABC
from typing import Dict

from hepbenchmarksuite.plugins.registry.interval_plugin import IntervalPlugin
from hepbenchmarksuite.plugins.timeseries import Timeseries


class TimeseriesCollectorPlugin(IntervalPlugin, ABC):

    def __init__(self, name: str, interval_mins: float, unit: str):
        super().__init__(interval_mins)
        self.unit = unit
        self.timeseries = Timeseries(name)

    def on_start(self) -> None:
        self.timeseries.clear()

    def on_end(self) -> Dict:
        report = self.timeseries.create_report()
        report['unit'] = self.unit
        report['interval'] = self.interval_secs
        return report
