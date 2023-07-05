import operator
import re
import statistics
from functools import reduce
from typing import Dict, Callable, List


class MetricDefinition:
    """
    The MetricDefinition class represents a single collection metric
    and all necessary attributes for acquiring values of this metric.
    """

    def __init__(self, name: str, options: Dict, interval_granularity_secs: float = 10):
        self.name = name
        self.interval_granularity_secs = interval_granularity_secs
        self.interval_mins: float = self._round_interval(options['interval_mins'])
        self.command: str = options['command'].strip()
        self.regex: str = options['regex']
        self.unit: str = options['unit']
        self.aggregation: str = 'sum'

        if 'aggregation' in options:
            self.aggregation: str = options['aggregation'].strip()

        self.agg_func = self._parse_aggregation(self.aggregation)

    def _round_interval(self, interval_mins: float):
        """
        The collection of metrics should be spaced with certain granularity.
        The interval of 18s and 20s should be the same granularity of 20s.
        """
        assert (interval_mins > 0)
        interval_secs = interval_mins * 60
        interval_rounded_secs = round(
            interval_secs / self.interval_granularity_secs) * self.interval_granularity_secs
        # The interval cannot be zero
        if interval_rounded_secs == 0:
            interval_rounded_secs = self.interval_granularity_secs
        interval_rounded_mins = interval_rounded_secs / 60
        return interval_rounded_mins

    def _parse_aggregation(self, aggregation_function_name: str) -> Callable[[List[float]], float]:
        aggregation_functions = {
            'sum': sum,
            'average': statistics.mean,
            'minimum': min,
            'maximum': max,
            'count': len,
            'product': lambda x: reduce(operator.mul, x, 1),
            'median': statistics.median,
            'mode': statistics.mode,
            'standard_deviation': statistics.stdev,
            'variance': statistics.variance
        }
        return aggregation_functions[aggregation_function_name]

    def parse(self, command_output: str):
        """
        Extracts the metric value from the command output.

        If more values are extracted, they are aggregated
        into a single value using the defined aggregation function.
        """
        compiled_pattern = re.compile(self.regex)

        matches = []
        for match in compiled_pattern.finditer(command_output):
            value = match['value']
            matches.append(float(value))

        result = self.agg_func(matches)
        return result

    def serialize_to_dict(self) -> Dict:
        return {
            'interval_mins': self.interval_mins,
            'command': self.command,
            'regex': self.regex,
            'unit': self.unit,
            'aggregation': self.aggregation,
        }

    def get_interval_in_secs(self) -> float:
        return self.interval_mins * 60
