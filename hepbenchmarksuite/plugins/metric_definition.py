import operator
import re
import math
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
        self.aggregation: str = params.get('aggregation', 'default').strip()
        self.statistics: str = params.get('statistics', 'default').strip()
        self.agg_func = self._parse_aggregation(self.aggregation) 

    def _check_params(self, params: Dict):
        """
        Checks that only the required or optional parameters were set.
        """
        required_params = {'command', 'regex', 'unit', 'interval_mins'}
        optional_params = {'aggregation', 'description', 'expected-value', 'example-output', 'statistics'}

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
    
    @staticmethod
    def safe_average(values: List[float]) -> float:
        if not values:
            return math.nan
        return statistics.mean(values)

    @staticmethod
    def safe_min(values: List[float]) -> float:
        if not values:
            return math.nan
        return min(values)

    @staticmethod
    def safe_max(values: List[float]) -> float:
        if not values:
            return math.nan
        return max(values)

    @staticmethod
    def safe_median(values: List[float]) -> float:
        if not values:
            return math.nan
        return statistics.median(values)

    @staticmethod
    def safe_mode(values: List[float]) -> float:
        if not values:
            return math.nan
        try:
            return statistics.mode(values)
        except statistics.StatisticsError:
            return math.nan

    @staticmethod
    def safe_standard_deviation(values: List[float]) -> float:
        # stdev requires at least two data points
        if len(values) < 2:
            return math.nan
        return statistics.stdev(values)

    @staticmethod
    def safe_sum(values: List[float]) -> float:
        if not values:
            return math.nan
        return sum(values)

    @staticmethod
    def safe_product(values: List[float]) -> float:
        if not values:
            return math.nan
        return reduce(operator.mul, values, 1)

    def _parse_aggregation(self, aggregation_function_name: str) -> callable:
        """
        Return a callable function that aggregates a list of floats based on the specified function name.
        """
        aggregation_functions = {
            'sum': self.safe_sum,
            'average': self.safe_average,
            'minimum': self.safe_min,
            'maximum': self.safe_max,
            'count': len,  # count is safe even for empty lists
            'product': self.safe_product,
            'median': self.safe_median,
            'mode': self.safe_mode,
            'standard_deviation': self.safe_standard_deviation,
        }

        # Handle "default" or empty string as 'average'
        if aggregation_function_name in ("default", ""):
            return aggregation_functions['average']
        
        if aggregation_function_name in aggregation_functions:
            return aggregation_functions[aggregation_function_name]

        # Handle custom quantile-based functions (e.g. 'q50' for the 50th percentile)
        if aggregation_function_name.startswith('q'):
            q_value_str = aggregation_function_name[1:]
            try:
                q_value = float(q_value_str) / 100.0  # Convert percentage to a decimal value
            except ValueError as e:
                raise ValueError(f"Invalid quantile function name: '{aggregation_function_name}'") from e

            if not (0 < q_value < 1):
                raise ValueError("Quantile value must be between 0 and 100.")

            # Return a lambda that safely computes the quantile
            def safe_quantile(values: List[float]) -> float:
                if not values:
                    return math.nan
                return float(np.quantile(values, q_value))
            return safe_quantile

        raise ValueError(f"Invalid aggregation function name: '{aggregation_function_name}'")

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
