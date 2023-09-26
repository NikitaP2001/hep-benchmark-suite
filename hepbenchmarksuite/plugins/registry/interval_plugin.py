from abc import abstractmethod
from datetime import datetime
from multiprocessing import Event

from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin


class IntervalPlugin(StatefulPlugin):
    """
    IntervalPlugin executes itself in regular intervals.
    """

    def __init__(self, interval_mins: float):
        super().__init__()
        seconds_per_minute = 60
        self.interval_secs = interval_mins * seconds_per_minute

    def run(self, stop_event: Event):
        start_time = datetime.now()

        # Run immediately after start up
        self.execute()
        time_until_next_execution = self._determine_time_until_next_execution(start_time)

        # The stop_event will time out each period unless
        # the parent process requests cancellation by setting
        # the stop_event. Upon the cancellation, the wait
        # method ends immediately.
        while not stop_event.wait(timeout=time_until_next_execution):
            self.execute()
            time_until_next_execution = self._determine_time_until_next_execution(start_time)

    def _determine_time_until_next_execution(self, start_time):
        time_now = datetime.now()
        time_elapsed_this_round = (time_now - start_time).total_seconds() % self.interval_secs
        time_until_next_execution = self.interval_secs - time_elapsed_this_round
        return time_until_next_execution

    @abstractmethod
    def execute(self) -> None:
        """
        This functionality is executed in regular intervals.
        """
