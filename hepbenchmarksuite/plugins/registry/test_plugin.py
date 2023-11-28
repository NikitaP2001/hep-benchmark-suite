import multiprocessing as mp
import os
from datetime import datetime
from time import sleep
from typing import Dict

from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin


class TestPlugin(StatefulPlugin):
    __test__ = False

    def __init__(self):
        super().__init__()
        self.counter = 0

    def run(self, stop_event: mp.Event) -> None:
        """
        Runs until the stop signal is received.
        """
        while not stop_event.is_set():
            self.counter += 1
            sleep(0)

    def on_end(self) -> Dict:
        """
        Returns statistics calculated from its state values.
        """
        return {
            "measurements": {
                datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"): self.counter
            },
            "statistics": {
                "mean": self.counter / 2,
                "std": self.counter / 1.5
            }
        }
