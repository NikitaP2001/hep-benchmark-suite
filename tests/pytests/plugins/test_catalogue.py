import yaml
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

        print("regex>> {}".format(item['regex']))
        print("example-output>> {}".format(item['example-output']))
        print("expected-value>> {}".format(item['expected-value']))
        value = metric.parse(item['example-output'])
        print("value>> {}".format(value))
        self.assertAlmostEqual(item['expected-value'], value)

class CatalogueJSONTester(unittest.TestCase):
    """
    As above but reading a different json structure
    """

    def test_catalogue(self):

        catalogue_file_path = 'hepbenchmarksuite/config/plugins_catalogue.json'
        with open(catalogue_file_path, "r") as file:
            catalogue_items = json.load(file)

        #print (catalogue_items['plugins'])
        for item in catalogue_items['plugins']['CommandExecutor']['metrics'].values():
            #print(item)
            self._test_catalogue_item(item)

    def _test_catalogue_item(self, item: Dict):
        #print(item)
        metric = MetricDefinition('metric', {
            'command': item['command'],
            'regex': item['regex'],
            'unit': item['unit'],
            'interval_mins': 1
        })

        print("regex>> {}".format(item['regex']))
        print("example-output>> {}".format(item['example-output']))
        print("expected-value>> {}".format(item['expected-value']))
        value = metric.parse(item['example-output'])
        print("value>> {}".format(value))
        self.assertAlmostEqual(item['expected-value'], value)

class CatalogueYMLTester(unittest.TestCase):
    """
    As above but reading the yml file
    """

    def test_catalogue(self):

        catalogue_file_path = 'hepbenchmarksuite/config/plugins_catalogue.yml'
        with open(catalogue_file_path, "r") as file:
            catalogue_items = yaml.safe_load(file)

        #print (catalogue_items['plugins'])
        for k, item in catalogue_items['plugins']['CommandExecutor']['metrics'].items():
            #print(item)
            self._test_catalogue_item(k, item)

    def _test_catalogue_item(self, k: str, item: Dict):
        print("\nAnalysing>> %s"%k)
        metric = MetricDefinition('metric', {
            'command': item['command'],
            'regex': item['regex'],
            'unit': item['unit'],
            'interval_mins': 1
        })

        print("regex>> {}".format(item['regex']))
        print("example-output>> {}".format(item['example-output']))
        print("expected-value>> {}".format(item['expected-value']))
        value = metric.parse(item['example-output'])
        print("value>> {}".format(value))
        self.assertAlmostEqual(item['expected-value'], value)