"""
Purposefully defines two plugins in a single file.
"""
from datetime import timedelta
from multiprocessing import Event

from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin


class PluginParameterless(StatefulPlugin):

    def __init__(self):
        super().__init__()

    def run(self, stop_event: Event):
        pass

    def on_end(self):
        pass


class PluginMultipleParameters(StatefulPlugin):

    def __init__(self, param1: timedelta, param2: str):
        super().__init__()
        self.param1 = param1
        self.param2 = param2

    def run(self, stop_event: Event):
        pass

    def on_end(self):
        pass
