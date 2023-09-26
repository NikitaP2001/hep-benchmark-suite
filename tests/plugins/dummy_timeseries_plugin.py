from hepbenchmarksuite.plugins.registry.timeseries_collector_plugin import TimeseriesCollectorPlugin


class DummyTimeseriesPlugin(TimeseriesCollectorPlugin):

    def __init__(self, interval_mins: float):
        super().__init__('dummy', interval_mins, 'unit')
        self.counter = -1

    def execute(self) -> None:
        self.counter += 1
        self.timeseries.append(self.counter)
