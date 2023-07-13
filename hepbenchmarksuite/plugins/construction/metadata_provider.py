from abc import ABC
from typing import List

from hepbenchmarksuite.exceptions import PluginMetadataException


class PluginParameter:

    def __init__(self, name: str, is_optional: bool):
        self.name = name
        self.optional = is_optional

    def get_name(self) -> str:
        return self.name

    def is_optional(self) -> bool:
        return self.optional


class PluginMetadata:
    """
    Represents an available plugin, which can be instantiated.
    """

    def __init__(self, name: str, parameters: List[PluginParameter],
                 class_type):
        self.name = name
        self.parameters = parameters
        self.class_type = class_type

    def get_name(self) -> str:
        return self.name

    def get_parameters(self) -> List[PluginParameter]:
        return self.parameters


class PluginMetadataProvider(ABC):
    """
    PluginMetadataProvider is responsible for providing the metadata
    about the available plugins.
    """

    def __init__(self):
        self.items: List[PluginMetadata] = []

    def get_items(self) -> List[PluginMetadata]:
        return self.items

    def get_item_by_name(self, name: str) -> PluginMetadata:
        for item in self.items:
            if item.name.lower() == name.lower():
                return item
        raise PluginMetadataException(f'A plugin with the name "{name}" has not been registered.')
