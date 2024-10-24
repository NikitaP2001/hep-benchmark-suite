import json
import unittest
from typing import Dict

from hepbenchmarksuite.plugins.metric_definition import MetricDefinition


class CatalogueTester(unittest.TestCase):
    """
    Tests that the regular expression of an item in the catalogue
    returns the expected value given the example output.

    It, however, does not test the command itself.
    """

    def test_catalogue(self):
        catalogue_file_path = 'examples/plugins/catalogue.json'
        with open(catalogue_file_path, "r") as file:
            catalogue_items = json.load(file)

        for item in catalogue_items:
            self._test_catalogue_item(item)

    def _test_catalogue_item(self, item: Dict):
        metric = MetricDefinition('metric', {
            'command': item['command'],
            'regex': item['regex'],
            'unit': item['unit'],
            'interval_mins': 1
        })

        value = metric.parse(item['example-output'])
        self.assertAlmostEqual(item['expected-value'], value)
