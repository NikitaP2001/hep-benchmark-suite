from multiprocessing import Event

from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin


class PluginWithOptionalParameter(StatefulPlugin):

    def __init__(self, mandatory: float, optional: int = -1):
        super().__init__()
        self.mandatory = mandatory
        self.optional = optional

    def run(self, stop_event: Event):
        pass

    def on_end(self):
        pass
