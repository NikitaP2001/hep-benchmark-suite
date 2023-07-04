import glob
import importlib
import inspect
import os
from types import ModuleType
from typing import List

from hepbenchmarksuite.exceptions import PluginMetadataException
from hepbenchmarksuite.plugins.construction.metadata_provider import PluginMetadataProvider, PluginMetadata, \
    PluginParameter
from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin


class DynamicPluginMetadataProvider(PluginMetadataProvider):

    def __init__(self, directory: str):
        super().__init__()
        self.directory = directory

    def initialize(self) -> None:
        """
        Registers plugin classes located in the directory.
        Skips classes that do not inherit from StatefulPlugin.
        """
        # Silently exist if the directory is non-existent.
        if not os.path.exists(self.directory):
            return
        # However, fail if the directory provided is actually a file.
        if not os.path.isdir(self.directory):
            raise PluginMetadataException(f'The path to the registry "{self.directory}" '
                                          f'provided is not a directory.')

        module_file_paths = self._read_directory_for_modules()

        for module_file_path in module_file_paths:
            module = self._import_module(module_file_path)
            self._register_plugins_from_module(module)

    def _read_directory_for_modules(self) -> List[str]:
        plugin_file_paths = glob.glob(os.path.join(self.directory, "*.py"))
        return plugin_file_paths

    def _import_module(self, module_file_path: str) -> ModuleType:
        """
        module_file_path can be either relative or absolute.
        """
        # Get the module name from the file path
        module_file_name = os.path.basename(module_file_path)
        module_name = os.path.splitext(module_file_name)[0]

        # Import the module
        if os.path.isabs(self.directory):
            """
            The package name is not known in the case of an absolute path. 
            
            The class name differs from a relative path import. 
            For example, given absolute path /foo/bar/baz/package/module.py, inside
            which a class called Plugin resides, the instance of the this class
            will be <module.Plugin>.
            
            Note that `isinstance` can return False when checking whether an object that
            was instantiated from a class imported using an absolute path is an instance
            of a class that is imported via a relative import (the package may differ).
            """
            spec = importlib.util.spec_from_file_location(module_name, module_file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            """
            In case of relative path, we can rely on the classical importing mechanism
            via `import_module`. It will search for the file in the location provided 
            by the `plugins_package_name`.
            
            Given that /foo/bar/baz is the PYTHONPATH, an instance of the Plugin class
            from the /foo/bar/baz/package/module.py will be <package.module.Plugin>.
            This is because the `plugins_package_name` is set to "package.module".
            """
            plugins_package_name = self.directory.replace(os.path.sep, '.')
            module = importlib.import_module("." + module_name, package=plugins_package_name)

        return module

    def _register_plugins_from_module(self, module) -> None:
        # Iterate items of the imported python module
        for module_item_name in dir(module):
            module_item = getattr(module, module_item_name)

            if not self._is_plugin(module_item):
                continue

            class_name = module_item.__name__
            parameters = self._get_constructor_parameters(module_item)
            metadata = PluginMetadata(class_name, parameters, module_item)

            self.items.append(metadata)

    def _is_plugin(self, item) -> bool:
        # Skip items that are not a class
        if not inspect.isclass(item):
            return False

        # Skip abstract classes
        if inspect.isabstract(item):
            return False

        # Skip classes that do not inherit from StatefulPlugin
        if type(item) != type(StatefulPlugin):
            return False

        return True

    def _get_constructor_parameters(self, obj) -> List[PluginParameter]:
        constructor_signature = inspect.signature(obj.__init__)
        parameters = list(constructor_signature.parameters.values())

        plugin_parameters = []
        for param in parameters:
            if param.name == 'self':
                continue

            is_optional = param.default != inspect.Parameter.empty
            plugin_parameter = PluginParameter(param.name, is_optional)
            plugin_parameters.append(plugin_parameter)
        return plugin_parameters
