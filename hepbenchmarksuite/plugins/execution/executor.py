import multiprocessing as mp
from abc import ABC, abstractmethod
from typing import List, Type

from hepbenchmarksuite.plugins.execution.strategy import ExecutionStrategy
from hepbenchmarksuite.plugins.stateful_plugin import StatefulPlugin


class PluginExecutor(ABC):

    def __init__(self):
        self.topmost = False

    def set_topmost(self) -> None:
        self.topmost = True

    @abstractmethod
    def start_plugins(self, stop_event: mp.Event, plugins_started: mp.Event):
        pass

    @abstractmethod
    def stop_plugins(self, plugins_started: mp.Event):
        pass


class CompositePluginExecutor(PluginExecutor):
    """
    Starts the nested plugin executor in its own execution context (a thread or a process)
    and forwards it the request to start the plugins.
    """

    def __init__(self, base_strategy: PluginExecutor, execution_strategy_type: Type[ExecutionStrategy]):
        super().__init__()
        self.base_strategy = base_strategy
        self.execution_strategy_type = execution_strategy_type
        self.worker = None

    def start_plugins(self, stop_event: mp.Event, plugins_started: mp.Event):
        self.worker = self.execution_strategy_type()
        self.worker.start(self.base_strategy.start_plugins, args=(stop_event, plugins_started))

        # Wait for the process or thread to finish if this instance is located in
        # a nested hierarchy not at the topmost position.
        if not self.topmost:
            self.stop_plugins(plugins_started)

    def stop_plugins(self, plugins_started: mp.Event):
        plugins_started.wait()
        self.worker.join()


class LeafPluginExecutor(PluginExecutor):
    """
    Starts all the given plugins in its respective execution contexts (threads or processes).
    """

    def __init__(self, plugins: List[StatefulPlugin], execution_strategy_type: Type[ExecutionStrategy]):
        super().__init__()
        self.plugins = plugins
        self.execution_strategy_type = execution_strategy_type
        self.workers = []

    def start_plugins(self, stop_event: mp.Event, plugins_started: mp.Event):
        # This method can be called from within a subprocess.
        # In such a case, the parent process can continue while this method is being set up.
        # Therefore, it has to be made thread safe, so that two stop_plugins
        # will not be executed until start_plugins has finished.
        for plugin in self.plugins:
            worker = self.execution_strategy_type()
            worker.start(plugin.start, args=(stop_event,))
            self.workers.append(worker)

        plugins_started.set()

        # Wait for the process or thread to finish if this instance is located in
        # the nested hierarchy not at the topmost position.
        if not self.topmost:
            self.stop_plugins(plugins_started)

    def stop_plugins(self, plugins_started: mp.Event):
        # Ensuring thread safety: plugins cannot be stopped before they
        # have all been started.
        plugins_started.wait()

        while len(self.workers) > 0:
            worker = self.workers.pop()
            worker.join()


class RootPluginExecutor:
    """
    RootPluginExecutor wraps the plugin executor to orchestrate it
    by keeping the stop_event and the plugins_started event.
    These events must be owned by the main process.
    """

    def __init__(self, base_executor: PluginExecutor):
        self.base_executor = base_executor
        self.stop_event = mp.Event()
        self.plugins_started = mp.Event()

    def start_plugins(self):
        self.stop_event.clear()
        self.plugins_started.clear()

        self.base_executor.set_topmost()
        self.base_executor.start_plugins(self.stop_event, self.plugins_started)

    def stop_plugins(self):
        self.stop_event.set()
        self.base_executor.stop_plugins(self.plugins_started)
