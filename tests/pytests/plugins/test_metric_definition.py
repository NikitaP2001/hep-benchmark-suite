import unittest
import math
import pytest
import statistics
from hepbenchmarksuite.exceptions import PluginBuilderException
from hepbenchmarksuite.plugins.metric_definition import MetricDefinition


class TestMetricDefinition(unittest.TestCase):

    def test_parse(self):
        params = {
            'command': 'none',
            'regex': r'V\d+: (?P<value>\d+).*',
            'unit': 'none',
            'aggregation': 'average',
            'interval_mins': 1
        }
        definition = MetricDefinition('metric', params)

        command_output = """
            V1: 10,
            V2: 40
        """
        value = definition.parse(command_output)
        expected_value = 25

        self.assertEqual(expected_value, value)

    def test_empty_parse_for_aggregations(self):
        # Define a mapping of aggregation names to expected output on empty input.
        # Note: adjust expected values if some functions (e.g. 'count') should return something different.
        aggregations_expected = {
            'average': math.nan,
            'sum': math.nan,
            'minimum': math.nan,
            'maximum': math.nan,
            'median': math.nan,
            'mode': math.nan,
            'product': math.nan,
            'standard_deviation': math.nan,
            'q50': math.nan,  # quantile-based aggregation example
        }
        
        for aggregation, expected in aggregations_expected.items():
            with self.subTest(aggregation=aggregation):
                params = {
                    'command': 'none',
                    'regex': r'V\d+: (?P<value>\d+).*',
                    'unit': 'none',
                    'aggregation': aggregation,
                    'interval_mins': 1
                }
                definition = MetricDefinition('metric', params)
                
                command_output = """
                    V1:,
                    V2:
                """
                value = definition.parse(command_output)
                
                if math.isnan(expected):
                    self.assertTrue(math.isnan(value))
                else:
                    self.assertEqual(value, expected)

    def test_aggregations(self):
        agg_list = [
            'sum',
            'average',
            'minimum',
            'maximum',
            'q25',
            'q50',
            'q75',
            'q85',
            'q150',
            'qnan',
            'count',
            'product',
            'median',
            'standard_deviation',
        ]

        params = {
            'command': 'none',
            'regex': r'V\d+: (?P<value>\d+).*',
            'unit': 'none',
            'aggregation': 'average',
            'interval_mins': 1
        }

        command_output = """
            V1: 10,
            V2: 40
        """

        expected_results = {
            'sum': 50.0,
            'average': 25.0,
            'minimum': 10.0,
            'maximum': 40.0,
            'q25': 17.5,
            'q50': 25.0,
            'q75': 32.5,
            'q85': 35.5,
            'q95': 38.5,
            'count': 2,
            'product': 400.0,
            'median': 25.0,
            'standard_deviation': statistics.stdev([10, 40]),
        }

        expected_exceptions = {
            'q150': ValueError,
            'qnan': ValueError,
        }

        for agg in agg_list:
            params['aggregation'] = agg
            if agg in expected_exceptions:
                with self.assertRaises(expected_exceptions[agg], msg=f"Aggregation '{agg}' did not raise expected exception"):
                    definition = MetricDefinition('metric', params)
                    definition.parse(command_output)
            else:
                definition = MetricDefinition('metric', params)
                value = definition.parse(command_output)
                expected_value = expected_results[agg]
                if isinstance(expected_value, float):
                    self.assertAlmostEqual(expected_value, value, places=5, msg=f"Aggregation '{agg}' failed")
                else:
                    self.assertEqual(expected_value, value, msg=f"Aggregation '{agg}' failed")
    
    def test_parse__ignores_everything_but_value(self):
        """
        The parsing function extracts a value denoted as "value".
        Unnamed groups or groups with different names are ignored.
        """
        params = {
            'command': 'none',
            'regex': r'(?P<value>\d+).(?P<value2>\d+)(.\d+)?',
            'unit': 'none',
            'interval_mins': 1
        }
        definition = MetricDefinition('metric', params)

        command_output = "10.20.50"
        value = definition.parse(command_output)
        expected_value = 10

        self.assertEqual(expected_value, value)

    def test_round_interval(self):
        """
        Test that intervals similar to each other are
        considered to be the same interval.
        """
        params = {
            'command': '',
            'regex': '',
            'unit': '',
            'interval_mins': 0.00061666666  # 37 ms in minutes
        }
        definition = MetricDefinition('metric', params)
        metric_config = definition.serialize_to_dict()

        # 10s in minutes
        expected_rounded_interval = 0.166666667
        self.assertAlmostEqual(expected_rounded_interval, metric_config['interval_mins'])

    def test_construction__superfluous_parameters(self):
        params = {
            'command': '',
            'regex': '',
            'unit': '',
            'interval_mins': 1,
            'superfluous_parameter': ''
        }

        def create_instance():
            MetricDefinition('metric', params)

        self.assertRaises(PluginBuilderException, create_instance)

    def test_construction__missing_parameters(self):
        params = {
            'command': '',
            'regex': '',
            'unit': '',
        }

        def create_instance():
            MetricDefinition('metric', params)

        self.assertRaises(PluginBuilderException, create_instance)
