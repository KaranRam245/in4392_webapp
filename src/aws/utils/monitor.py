from abc import ABC, abstractmethod
from queue import PriorityQueue

from aws.utils.packets import HeartBeatPacket


class Observable:

    def __init__(self):
        self._listeners = []

    def notify(self, message):
        for listener in self._listeners:
            listener.event(message)

    def add_listener(self, instance):
        """
        Add a listener to the Observable pattern.
        :param instance: Instance that will subscribe to the observable pattern.
        :return:
        """
        self._listeners.append(instance)


class Listener(ABC):

    @abstractmethod
    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format or heartbeat format.
        """
        raise NotImplementedError("The class is a listener but has not implemented the event "
                                  "method.")
