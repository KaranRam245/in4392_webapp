"""
Module for the Node Worker.
"""
from aws.utils.monitor import Observable, Monitor


class WorkerCore(Observable):
    """
    The WorkerCore accepts the task from the Node Manager.
    """

    def run(self):
        """
        Start function for the WorkerCore.
        """
        raise NotImplementedError()


class WorkerMonitor(Monitor):

    def __init__(self):
        pass

    def run(self):
        """
        Run the Monitor class.
        """
        raise NotImplementedError()

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format.
        """
        raise NotImplementedError("The class is a listener but has not implemented the event "
                                  "method.")
