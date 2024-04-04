import unittest
from statistics import mean, median, stdev
import numpy as np
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

    def test_parse__multiple_metrics(self):
        """
        The parsing function should correctly handled more than one metric provided.
        """
        params = {
            'command': 'none',
            'regex': r'F\d+: (?P<value>\d+\.\d+).*',
            'unit': 'none',
            'aggregation': 'average,sum,minimum,maximum,median,standard_deviation,count',
            'interval_mins': 1
        }
        definition = MetricDefinition('metric', params)

        command_output = """
            F1: 2.84,
            F2: 2.89,
            F3: 2.55,
            F4: 2.51,
            F5: 2.64,
            F6: 2.46,
            F7: 2.66,
            F8: 2.39,
            F9: 2.48,
            F10: 2.17,
            F11: 2.36,
            F12: 2.68,
            F13: 2.83,
            F14: 2.36,
            F15: 2.42,
            F16: 2.53,
            F17: 2.60,
            F18: 2.46,
            F19: 2.70,
            F20: 2.40,
            F21: 2.20,
            F22: 2.46,
            F23: 2.49,
            F24: 2.28,
            F25: 2.59,
            F26: 2.65,
            F27: 2.39,
            F28: 2.60,
        """
        values = definition.parse(command_output)
        output_list = [2.84, 2.89, 2.55, 2.51, 2.64, 2.46, 2.66, 2.39, 2.48, 2.17, 2.36, 2.68, 2.83, 2.36, 2.42, 2.53, 2.6, 2.46, 2.7, 2.4, 2.2, 2.46, 2.49, 2.28, 2.59, 2.65, 2.39, 2.6]

        self.assertEqual([mean(output_list), sum(output_list), min(output_list), max(output_list), median(output_list), stdev(output_list), len(output_list)], values)
    
    def test_parse__multiple_metrics__quantiles(self):
        """
        The parsing function should correctly handled more than one metric provided and calculate quantiles.
        """
        params = {
            'command': 'none',
            'regex': r'F\d+: (?P<value>\d+\.\d+).*',
            'unit': 'none',
            'aggregation': 'minimum,q25,average,q75,maximum,median',
            'interval_mins': 1
        }
        definition = MetricDefinition('metric', params)

        command_output = """
            F1: 2.84,
            F2: 2.89,
            F3: 2.55,
            F4: 2.51,
            F5: 2.64,
            F6: 2.46,
            F7: 2.66,
            F8: 2.39,
            F9: 2.48,
            F10: 2.17,
            F11: 2.36,
            F12: 2.68,
            F13: 2.83,
            F14: 2.36,
        """
        values = definition.parse(command_output)
        output_list = [2.84, 2.89, 2.55, 2.51, 2.64, 2.46, 2.66, 2.39, 2.48, 2.17, 2.36, 2.68, 2.83, 2.36]

        self.assertEqual([min(output_list), np.quantile(output_list, 0.25), mean(output_list), np.quantile(output_list, 0.75), max(output_list), median(output_list)], values)
    
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
