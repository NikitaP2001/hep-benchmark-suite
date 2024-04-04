import operator
import re
import statistics
import numpy as np
from functools import reduce
from typing import Dict, Callable, List

from hepbenchmarksuite.exceptions import PluginBuilderException


class MetricDefinition:
    """
    The MetricDefinition class represents a single collection metric
    and all necessary attributes for acquiring values of this metric.
    """

    def __init__(self, name: str, params: Dict, interval_granularity_secs: float = 10):
        self.name = name
        self.interval_granularity_secs = interval_granularity_secs

        self._check_params(params)

        self.interval_mins: float = self._round_interval(params['interval_mins'])
        self.command: str = params['command'].strip()
        self.regex: str = params['regex']
        self.unit: str = params['unit']
        if len(params.get('aggregation', 'sum').split(","))<=1:
            self.aggregation: str = params.get('aggregation', 'sum').strip()
        else:
            self.aggregation: List =[x.strip() for x in params.get('aggregation', 'sum').split(",")]
        if isinstance(self.aggregation, str):
            self.agg_func = self._parse_aggregation(self.aggregation) 
        else:
             self.agg_func = [self._parse_aggregation(agg) for agg in self.aggregation]

    def _check_params(self, params: Dict):
        """
        Checks that only the required or optional parameters were set.
        """
        required_params = {'command', 'regex', 'unit', 'interval_mins'}
        optional_params = {'aggregation', 'description', 'expected-value', 'example-output'}

        given_params = set(params.keys())
        required_given = given_params - optional_params

        if required_given != required_params:
            raise PluginBuilderException(f'Invalid argument to {MetricDefinition.__name__}. '
                                         f'Required: {required_params}, optional: {optional_params},'
                                         f' given: {given_params}')

    def _round_interval(self, interval_mins: float):
        """
        The collection of metrics should be spaced with certain granularity.
        The interval of 18s and 20s should be the same granularity of 20s.
        """
        assert interval_mins > 0
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
            'q25': lambda x: np.quantile(x, 0.25),
            'q75': lambda x: np.quantile(x, 0.75),
            'count': len,
            'product': lambda x: reduce(operator.mul, x, 1),
            'median': statistics.median,
            'mode': statistics.mode,
            'standard_deviation': statistics.stdev,
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
        result = [agg(matches) for agg in self.agg_func] if isinstance(self.agg_func, list) else self.agg_func(matches)
        
        return result

    def serialize_to_dict(self) -> Dict:
        """
        Returns a dictionary containing the parameters.
        """
        return {
            'interval_mins': self.interval_mins,
            'command': self.command,
            'regex': self.regex,
            'unit': self.unit,
            'aggregation': self.aggregation,
        }

    def get_interval_in_secs(self) -> float:
        return self.interval_mins * 60
