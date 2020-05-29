"""
Module for the Node Manager.
"""
from aws.utils.monitor import Listener, Observable


class TaskPool(Observable):
    """
    The TaskPool accepts the tasks from the user.
    """
    def __init__(self):
        self._tasks = []
        super().__init__()

    def run(self):
        """
        Start function for the TaskPool.
        """
        raise NotImplementedError()

    def add_task(self, task):
        """
        Add a new task to the TaskPool.
        :return:
        """
        raise NotImplementedError()


class TaskPoolMonitor(Listener):

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