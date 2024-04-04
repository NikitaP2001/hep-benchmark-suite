from datetime import datetime
import numpy as np
from typing import Dict, Any


class Timeseries:
    """
    Maintains a collection of values together
    with timestamps.

    The collected values can be used to create
    statistics or a summary report.
    """

    def __init__(self, name: str):
        self.name = name
        self.values = {}

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
        timeseries_data = self.values.values()
        timeseries_array = np.array(list(timeseries_data))
        if len(timeseries_data) > 0:
            return {
                'min': np.min(timeseries_array),
                'q25': np.quantile(timeseries_array, 0.25),
                'mean': np.mean(timeseries_array),
                'median': np.mean(timeseries_array),
                'q75': np.quantile(timeseries_array, 0.75),
                'max': np.max(timeseries_array)
            }
        return {}

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
