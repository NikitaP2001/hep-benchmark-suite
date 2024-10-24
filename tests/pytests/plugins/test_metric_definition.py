import unittest
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
