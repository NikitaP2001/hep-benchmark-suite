import logging
import math
from datetime import datetime
from math import inf
from multiprocessing import Event
from typing import Dict, List, Tuple

from hepbenchmarksuite.plugins.metric_definition import MetricDefinition
from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin
from hepbenchmarksuite.plugins.timeseries import Timeseries
from hepbenchmarksuite.utils import run_separated_commands

_log = logging.getLogger(__name__)

class BashCommandFailedException(Exception):
    pass


class CommandExecutor(StatefulPlugin):
    r"""
    CommandExecutor serves as an abstraction over executing different
    command utilities and retrieving some values from their output.

    If two metrics require the execution of the same command multiple times,
    it is executed only once.

    The following shows an example portion of a config that correctly
    configures this plugin:

    plugins:
        CommandExecutor:
            metrics:
                cpu-frequency:
                    command: cpupower frequency-info -f
                    regex: "current CPU frequency: (?P<value>\d+).*"
                    unit: kHz
                    interval_mins: 1
                power-consumption:
                    command: ipmitool sdr elist
                    regex: "PS \d Output.* (?P<value>\d+) Watts"
                    unit: W
                    interval_mins: 1
                used-memory:
                    command: free -m
                    regex: 'Mem: *(\d+) *(?P<value>\d+).*'
                    unit: MiB
                    interval_mins: 1
    """

    def __init__(self, metrics: Dict[str, Dict], interval_granularity_secs: float = 10):
        super().__init__()
        self.interval_granularity_secs = interval_granularity_secs
        self.metrics: Dict[str, MetricDefinition] = dict()
        self.timeseries: Dict[str, Timeseries] = dict()
        self.command_results = dict()
        self._initialize(metrics)

    def _initialize(self, metrics: Dict[str, Dict]) -> None:
        for metric_name, metric_options in metrics.items():
            self.metrics[metric_name] = MetricDefinition(metric_name, metric_options,
                                                         self.interval_granularity_secs)
            self.timeseries[metric_name] = Timeseries(metric_name)

    def _determine_unique_commands(self, metrics: List[MetricDefinition]):
        """
        Creates a set of commands as there is
        no need to execute the same command twice.
        """
        unique_commands = set()
        for metric in metrics:
            command = metric.command
            unique_commands.add(command)
        return unique_commands

    def on_start(self) -> None:
        for timeseries in self.timeseries.values():
            timeseries.clear()

    def run(self, stop_event: Event):
        start_time = datetime.now()

        # Run immediately after start up
        self.execute(list(self.metrics.values()))
        time_now = datetime.now()
        time_until_next_execution, next_metrics_to_collect = self._determine_time_until_next_execution(start_time,
                                                                                                       time_now)
        # The stop_event will time out each period unless
        # the parent process requests cancellation by setting
        # the stop_event. Upon the cancellation, the wait
        # method ends immediately.
        while not stop_event.wait(timeout=time_until_next_execution):
            self.execute(next_metrics_to_collect)
            time_now = datetime.now()
            time_until_next_execution, next_metrics_to_collect = self._determine_time_until_next_execution(start_time,
                                                                                                           time_now)

    def _determine_time_until_next_execution(
            self, start_time: datetime, time_now: datetime) -> Tuple[float, List[MetricDefinition]]:
        """
        Determines which interval is to be run next. It is possible that multiple
        groups should be executed. E.g., intervals of 1 and 5 minutes will be
        executed together every five minutes.

        Args:
            start_time: The time of when the execution started.

        Returns:
            Tuple of time until next execution and the groups (intervals) which should be run next round.
        """
        groups_to_run = set()
        shortest_time = inf

        for metric in self.metrics.values():
            interval = metric.get_interval_in_secs()
            time_elapsed_this_round = (time_now - start_time).total_seconds() % interval
            time_until_next_execution = interval - time_elapsed_this_round

            if math.isclose(time_until_next_execution, shortest_time):
                groups_to_run.add(metric)
            # Shorter time, will be executed sooner.
            if time_until_next_execution < shortest_time:
                shortest_time = time_until_next_execution
                groups_to_run.clear()
                groups_to_run.add(metric)

        return shortest_time, list(groups_to_run)

    def execute(self, metrics_to_collect: List[MetricDefinition]) -> None:
        _log.debug('Executing plugin "%s"', CommandExecutor.__name__)
        self._execute_commands(metrics_to_collect)
        self._parse_outputs(metrics_to_collect)

    def _execute_commands(self, metrics_to_collect: List[MetricDefinition]):
        """
        Executes the commands of all metrics.
        """
        unique_commands = self._determine_unique_commands(metrics_to_collect)
        self.command_results.clear()
        for command in unique_commands:
            result = CommandExecutor.run_command(command)
            self.command_results[command] = result

    def _parse_outputs(self, metrics_to_collect):
        """
        The command outputs are searched for relevant values,
        and then they are appended to the corresponding timeseries.
        """
        for metric_definition in metrics_to_collect:
            output = self.command_results[metric_definition.command]
            value = metric_definition.parse(output)
            self.timeseries[metric_definition.name].append(value)

    def on_end(self) -> Dict:
        report = dict()
        for timeseries in self.timeseries.values():
            timeseries_report = self._compose_report_for_metric(timeseries)
            report[timeseries.get_name()] = timeseries_report
        return report

    def _compose_report_for_metric(self, timeseries: Timeseries):
        report = timeseries.create_report()
        report['config'] = self.metrics[timeseries.get_name()].serialize_to_dict()
        return report

    @staticmethod
    def run_command(command: str):
        """
        Runs a command
        """
        return_code, reply, error = run_separated_commands(command)
        if return_code != 0:
            raise BashCommandFailedException(
                f'Subprocess returned non-zero return code. '
                f'Message: {error}'
            )
        return reply
