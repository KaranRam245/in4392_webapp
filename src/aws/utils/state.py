"""
Shared methods for state indication.
"""


class State:
    """
    Class for the indication of the current state of an instance.
    """

    # States of the instance based on the Amazon Elastic Compute Cloud.
    NEW = 0  # When starting up and not yet ready for receiving tasks.
    PENDING = 1  # When the instance has been started but has not yet received a task.
    RUNNING = 2  # When computing or managing.
    STOPPING = 3  # When the stop comment has been received.
    ERROR = 4  # When an error has occured.

    def __init__(self, state):
        """
        Initialize a State object indicating the current state of an instance.
        :param state: Initiger indicating the current state.
        """
        assert 0 <= state <= 4
        self._state = state

    def is_state(self, state) -> bool:
        return self._state == state

class TaskState(State):
    '''
    Class for the indication of the current state of a task
    '''
    UPLOADING=0
    READY=1
    RUNNING=2
    DONE=3

    def __init__(self, state):
        """
        Initialize a State object indicating the current state of a task.
        :param state: Initiger indicating the current state.
        """
        assert 0 <= state <= 3
        super().__init__(state)