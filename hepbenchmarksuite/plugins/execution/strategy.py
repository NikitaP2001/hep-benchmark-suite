import multiprocessing as mp
import threading
from abc import ABC, abstractmethod


class ExecutionStrategy(ABC):

    @abstractmethod
    def start(self, target_func, args):
        ...

    @abstractmethod
    def join(self):
        ...


class ExceptionPropagatingProcess(mp.Process):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exception = mp.Queue()

    def run(self):
        try:
            super().run()
        except BaseException as e:
            self.exception.put(e)

    def join(self, *args, **kwargs):
        super().join(*args, **kwargs)
        if not self.exception.empty():
            raise self.exception.get()


class ProcessExecutionStrategy(ExecutionStrategy):

    def __init__(self):
        self.process = None

    def start(self, target_func, args):
        self.process = ExceptionPropagatingProcess(target=target_func, args=args)
        self.process.start()

    def join(self):
        self.process.join()
        # Setting to None for safety (early failure in
        # case of invalid state)
        self.process = None


class ExceptionPropagatingThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exception = None

    def run(self):
        self.exception = None
        try:
            super().run()
        except BaseException as e:
            self.exception = e

    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception


class ThreadExecutionStrategy(ExecutionStrategy):

    def __init__(self):
        self.thread = None

    def start(self, target_func, args):
        self.thread = ExceptionPropagatingThread(target=target_func, args=args)
        self.thread.start()

    def join(self):
        self.thread.join()
        # Setting to None for safety (early failure in
        # case of invalid state)
        self.thread = None
