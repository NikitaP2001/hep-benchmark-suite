from datetime import datetime
import numpy as np
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
        Computes a set of statistical metrics based on the specified configuration.
        If no specific statistics are provided, it returns default set of statistics..
        """
        timeseries_data = self.values.values()
        timeseries_array = np.array(list(timeseries_data))

        # Return an empty dictionary if timeseries is empty
        if len(timeseries_array) == 0:
            return {}

        predefined_stats_functions = {
            'min': np.min,
            'mean': np.mean,
            'median': np.median,
            'max': np.max
        }

        # Determine the list of statistics to compute
        if self.statistics == 'default':
            # Default statistics
            statistics_list = ['min', 'q25', 'mean', 'median', 'q75', 'q85', 'q95', 'max']
        else:
            # Parse user-specified statistics
            statistics_list = [stat.strip() for stat in self.statistics.split(',') if stat.strip()]

        user_statistics = {}
        for stat in statistics_list:
            if stat in predefined_stats_functions:
                # Compute predefined statistics
                user_statistics[stat] = predefined_stats_functions[stat](timeseries_array)
                continue

            # Handle quantile-based statistics
            if stat.startswith('q'):
                q_value_str = stat[1:] # Extract numeric part of quantile
                try:
                    q_value = float(q_value_str) / 100.0 # Convert percentage a to decimal value
                    if not (0 <= q_value <= 1): # Validate quantile range
                        raise ValueError
                except ValueError as e:
                    # Raise error for invalid quantile format
                    raise ValueError(f"Invalid quantile value: '{stat}'. Quantile must be between q0 and q100.") from e
                # Compute quantile
                user_statistics[stat] = np.quantile(timeseries_array, q_value)
                continue
            # Raise an error for unsupported statistics
            raise ValueError(f"Statistic '{stat}' not supported.")

        return user_statistics

    def create_report(self) -> Dict:
        statistics = self.calculate_statistics()
        timestamps = list(self.get_values().keys())
        values = list(self.get_values().values())
        start_time = timestamps[0]
        end_time = timestamps[-1]

        report = {
            'start_time': start_time,
            'end_time': end_time,
            'values': values,
            'statistics': statistics
        }
        return report
