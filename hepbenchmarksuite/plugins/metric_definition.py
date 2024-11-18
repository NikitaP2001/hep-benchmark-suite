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
        self.aggregation: str = params.get('aggregation', 'sum').strip()
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

    def _parse_aggregation(self, aggregation_function_name: str) -> Callable[[List[float]], float]:
        """
        Parses the given aggregation function name and returns the corresponding callable function.

        Supported aggregation functions include standard functions like 'sum', 'average', 'minimum', etc.,
        as well as custom quantile-based functions starting with 'q' followed by a number.
        """
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
        }

        # Return the standard aggregation function if it exists in the dictionary
        if aggregation_function_name in aggregation_functions:
            return aggregation_functions[aggregation_function_name]

        # Handle custom quantile-based functions starting with 'q'
        if aggregation_function_name.startswith('q'):
            q_value_str = aggregation_function_name[1:] # Extract the numeric part after 'q'
            try:
                q_value = float(q_value_str) / 100.0 # Convert percentage to a decimal value
            except ValueError as e:
                # Raise an error if the quantile value is not a valid number
                raise ValueError(f"Invalid quantile function name: '{aggregation_function_name}'") from e

            # Ensure the quantile value is within the valid range (0, 100)
            if not (0 < q_value < 1):
                raise ValueError("Quantile value must be between 0 and 100.")

             # Return a lambda function to calculate the specified quantile 
            return lambda x: np.quantile(x, q_value)
            
        # Raise an error if the function name is invalid
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
