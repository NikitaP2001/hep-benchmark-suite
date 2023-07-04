import unittest
from multiprocessing import Event
from typing import Any

from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin


class FailingPlugin(StatefulPlugin):

    def run(self, stop_event: Event) -> None:
        raise RuntimeError('A test error message.')

    def on_end(self) -> Any:
        return dict()


class SuccessfulPlugin(StatefulPlugin):

    def run(self, stop_event: Event) -> None:
        pass

    def on_end(self) -> Any:
        return dict()


class TestStatefulPlugin(unittest.TestCase):

    def test_start__sets_status_upon_exception(self):
        plugin = FailingPlugin()
        plugin.start(Event())

        result = plugin.get_result()

        self.assertEqual(2, len(result.keys()))
        self.assertEqual('failure', result['status'])
        self.assertEqual('RuntimeError("A test error message.")', result['error_message'])

    def test_start__sets_status_success(self):
        plugin = SuccessfulPlugin()
        plugin.start(Event())

        result = plugin.get_result()

        self.assertEqual(1, len(result.keys()))
        self.assertEqual('success', result['status'])
