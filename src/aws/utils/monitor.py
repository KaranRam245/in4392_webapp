from abc import ABC, abstractmethod


class Monitor(ABC):

    @abstractmethod
    def run(self):
        pass
