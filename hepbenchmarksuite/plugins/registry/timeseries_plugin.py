import datetime
from abc import abstractmethod
from datetime import datetime
from multiprocessing import Event
from statistics import mean
from typing import Dict, Any

from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin
from hepbenchmarksuite.utils import run_piped_commands


class BashCommandFailedException(Exception):
    pass


class TimeseriesCollectorPlugin(StatefulPlugin):

    def __init__(self, interval_mins: float, unit: str):
        super().__init__()
        self.unit = unit

        seconds_per_minute = 60
        self.interval_secs = interval_mins * seconds_per_minute
        self.collected_metrics = dict()

    def on_start(self) -> None:
        self.collected_metrics.clear()

    def run(self, stop_event: Event):
        start_time = datetime.now()

        # Run immediately after start up
        value = self.collect_metric()
        self._append_metric(value)
        time_until_next_execution = self._determine_time_until_next_execution(start_time)

        # The stop_event will time out each period unless
        # the parent process requests cancellation by setting
        # the stop_event. Upon the cancellation, the wait
        # method ends immediately.
        while not stop_event.wait(timeout=time_until_next_execution):
            value = self.collect_metric()
            self._append_metric(value)

            time_until_next_execution = self._determine_time_until_next_execution(start_time)

    @abstractmethod
    def collect_metric(self):
        """
        Collects timeseries data.
        """
        pass

    def _append_metric(self, value: Any) -> None:
        """
        Appends collected metrics in the format:
        {
            timestamp1: value1,
            timestamp2: value2,
            timestamp3: value3
        }
        """
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        self.collected_metrics[timestamp] = value

    def _determine_time_until_next_execution(self, start_time):
        time_now = datetime.now()
        time_elapsed_this_round = (time_now - start_time).total_seconds() % self.interval_secs
        time_until_next_execution = self.interval_secs - time_elapsed_this_round
        return time_until_next_execution

    def on_end(self):
        statistics = self._calculate_statistics()
        timestamps = list(self.collected_metrics.keys())
        values = list(self.collected_metrics.values())

        result = {
            'interval': self.interval_secs,
            'tstart': timestamps[0],
            'tend': timestamps[-1],
            'unit': self.unit,
            'values': values,
            'statistics': statistics
        }
        return result

    def _calculate_statistics(self) -> Dict[str, float]:
        # TODO: add desired statistics
        timeseries_data = self.collected_metrics.values()
        if len(timeseries_data) > 0:
            return {
                'min': min(timeseries_data),
                'mean': mean(timeseries_data),
                'max': max(timeseries_data)
            }
        else:
            return dict()

    def run_command(self, command: str):
        """
        Runs a command
        """
        return_code, reply, error = run_piped_commands(command)
        if return_code != 0:
            raise BashCommandFailedException(
                f'Subprocess returned non-zero return code. '
                f'Message: {error}'
            )
        return reply
