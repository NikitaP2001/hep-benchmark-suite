from abc import ABC, abstractmethod
from typing import List, Any

from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin


class PluginBuilder(ABC):

    @abstractmethod
    def build(self) -> List[StatefulPlugin]:
        pass


class PluginConfigParameter:

    def __init__(self, name: str, value: Any):
        self.name = name
        self.value = value

    def get_name(self) -> str:
        return self.name

    def get_value(self) -> Any:
        return self.value


class PluginConfigItem:

    def __init__(self, name: str, parameters: List[PluginConfigParameter]):
        self.name = name
        self.parameters = parameters

    def get_name(self) -> str:
        return self.name

    def get_parameters(self) -> List[PluginConfigParameter]:
        return self.parameters
