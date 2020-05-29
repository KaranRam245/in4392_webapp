"""
Module for the Resource Manager.
"""
from aws.utils.monitor import Listener


class ResourceManagerCore:

    def __init__(self):
        pass

    def run(self):
        raise NotImplementedError()


class ResourceMonitor(Listener):

    def __init__(self):
        pass

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format.
        """
        raise NotImplementedError("The class is a listener but has not implemented the event "
                                  "method.")