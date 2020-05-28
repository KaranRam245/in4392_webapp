"""
Module for the Node Manager.
"""
from aws.utils.monitor import Monitor


class TaskPool:
    """
    The TaskPool accepts the tasks from the user.
    """
    def __init__(self):
        pass

    def run(self):
        """
        Start function for the TaskPool.
        """
        raise NotImplementedError()

    def add_task(self):
        """
        Add a new task to the TaskPool.
        :return:
        """
        raise NotImplementedError()


class TaskPoolMonitor(Monitor):

    def __init__(self):
        pass

    def run(self):
        raise NotImplementedError()