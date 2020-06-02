"""
Module for the Node Manager.
"""
from aws.utils.monitor import Listener, Observable
from aws.utils.state import TaskState


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

    def add_task(self,task:Task):
        """
        Add a new task to the TaskPool.
        """
        self._tasks.append(task)


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


class Task:
    '''Task contains all information with regards to a tasks in the TaskPool'''

    TEXT=0
    CSV=1

    def __init__(self, data, dataType):
        self.data = data
        self.taskType = dataType
        self.state = TaskState.UPLOADING

    def get_task_type(self):
        return self.taskType

    def get_task_data(self):
        return self.data

    def get_task_state(self):
        return self.state
