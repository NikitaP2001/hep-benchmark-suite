from multiprocessing import Event

from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin


class PluginSingleParameter(StatefulPlugin):

    def __init__(self, param: int):
        super().__init__()
        self.param = param

    def run(self, stop_event: Event):
        pass

    def on_end(self):
        pass


DummyFieldThatIsNotClass = list()
