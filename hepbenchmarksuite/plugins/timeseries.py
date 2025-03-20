from datetime import datetime
import numpy as np
import math
from typing import Dict, Any, Optional


class Timeseries:
    """
    Maintains a collection of values together
    with timestamps.

    The collected values can be used to create
    statistics or a summary report.
    """

    def __init__(self, name: str, statistics: Optional[str] = 'default'):
        self.name = name
        self.values = {}
        self.statistics = statistics

    def get_name(self) -> str:
        return self.name

    def get_values(self) -> Dict:
        return self.values

    def get_last(self):
        return list(self.values.values())[-1]

    def clear(self) -> None:
        self.values.clear()

    def append(self, value: Any) -> None:
        timestamp_utc = datetime.utcnow()
        timestamp_utc_string = timestamp_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        self.values[timestamp_utc_string] = value

    def calculate_statistics(self) -> Dict[str, float]:
        """
        Computes a set of statistical metrics for the time series data.
        Handles user-specified statistics or defaults to a predefined set.
        """
        # Convert values to a NumPy array and filter out NaN values
        timeseries_array = np.array(list(self.values.values()))
        valid_values = timeseries_array[~np.isnan(timeseries_array)]

        # Return an empty dictionary if no data is present
        if len(timeseries_array) == 0:
            return {}
        
        # Return an empty dictionary if no data is present
        if len(valid_values) == 0:
            return {
                'total_count': len(timeseries_array),
                'valid_count': 0,
                'min': math.nan,
                'max': math.nan,
                'mean': math.nan,
                'median': math.nan,
            }

        # Predefined statistical functions
        predefined_stats = {'min': np.min, 'mean': np.mean, 'median': np.median, 'max': np.max}

        # Determine the list of statistics to compute (default or user-specified)
        statistics_list = (
            ['min', 'q25', 'mean', 'median', 'q75', 'q85', 'q95', 'max']
            if self.statistics == 'default'
            else [stat.strip() for stat in self.statistics.split(',') if stat.strip()]
        )

        # Initialize result with basic counts
        result = {'total_count': len(timeseries_array), 'valid_count': len(valid_values)}

        # Compute statistics
        for stat in statistics_list:
            if stat in predefined_stats:
                # Calculate predefined statistics
                result[stat] = predefined_stats[stat](valid_values) if len(valid_values) > 0 else math.nan
            elif stat.startswith('q'):
                # Calculate quantile-based statistics
                try:
                    quantile_str = stat[1:]
                    quantile = float(quantile_str) / 100.0
                    if not (0 <= quantile <= 1):
                        raise ValueError(f"Quantile '{quantile_str}' is out of bounds. Must be between q0 and q100.")
                    result[stat] = np.quantile(valid_values, quantile)
                except ValueError:
                    raise ValueError(f"Invalid quantile value: '{stat}'. Must be a valid number between q0 and q100.")
            else:
                # Raise an error for unsupported statistics
                raise ValueError(f"Statistic '{stat}' not supported.")
        
        return result

    def create_report(self) -> Dict:
        """
        Generates a report summarizing the time series data, including statistics,
        start and end timestamps, and the list of values.
        """
        if not self.values:  # Handle empty Timeseries
            return {
                'start_time': None,
                'end_time': None,
                'values': [],
                'statistics': {}
            }

        statistics = self.calculate_statistics()
        timestamps = list(self.get_values().keys())
        values = list(self.get_values().values())

        # Extract start and end times
        start_time = timestamps[0]
        end_time = timestamps[-1]

        # Build and return the report
        return {
            'start_time': start_time,
            'end_time': end_time,
            'values': values,
            'statistics': statistics
        }
