import multiprocessing as mp
from abc import ABC, abstractmethod
from multiprocessing import Event
from typing import Dict

from hepbenchmarksuite.exceptions import PluginAssertError


class StatefulPlugin(ABC):

    def __init__(self):
        self.manager = mp.Manager()
        self.queue = self.manager.Queue()

    def start(self, stop_event: Event) -> None:
        """
        Starts the execution of the plugin and
        puts the results into a queue once it finishes.
        """
        try:
            self.on_start()
            self.run(stop_event)
            result = self.on_end()
            result['status'] = 'success'
        except Exception as e:
            message = f'{type(e).__name__}("{str(e)}")'
            result = {
                'status': 'failure',
                'error_message': message
            }
        self.queue.put(result)

    def get_result(self) -> Dict:
        """
        Returns the result produced by the plugin.

        It cannot be called while the plugin is still running.
        """
        if self.queue.empty():
            raise PluginAssertError('No results available: Cannot retrieve the result of a plugin when '
                                    'the plugin is still running or has not been started.')

        return self.queue.get()

    def on_start(self) -> None:
        """
        Executed before the main plugin starts.
        This is the optimal place for setting up necessary resources, configurations,
        or connections needed by the plugin.
        """
        pass

    @abstractmethod
    def run(self, stop_event: Event) -> None:
        """
        Starts the main functionality of the plugin.
        It should check for the `stop_event` being set
        if it is running in an infinite loop.

        Args:
            stop_event: An event that signals whether the plugin should stop running.
        """
        pass

    @abstractmethod
    def on_end(self) -> Dict:
        """
        Executed after the plugin finishes running.
        Any resources initialized in `on_start` will be disposed of here.

        Returns:
             Any results produced by the plugin.
        """
        pass
