"""
Shared methods for state indication.
"""


class State:
    """
    Class for the indication of the current state of an instance.
    """

    def __init__(self, state):
        self._state = state

    def get_state(self):
        return self._state

    def set_state(self, state):
        self._state = state

    def is_state(self, state) -> bool:
        return self._state == state


class ProgramState(State):

    # States of the program based on the Amazon Elastic Compute Cloud.
    # Note that this state is different from the EC2 instance state.
    NEW = 0  # When the instance started but has not initialized yet.
    PENDING = 1  # When the instance has been started but has not yet received a task.
    RUNNING = 2  # When computing or managing.
    STOPPING = 3  # When the stop comment has been received.
    ERROR = 4  # When an error has occured.

    def __init__(self, state):
        """
        Initialize a State object indicating the current state of a program.
        :param state: Initiger indicating the current state.
        """
        assert 0 <= state <= 4
        super().__init__(state)


class InstanceState(State):

    # States of the instance based on the EC2 instance states.
    # Note that this state is different from the EC2 instance state.
    PENDING = 0  # When the instance has been started but has not yet received a task.
    RUNNING = 1  # When computing or managing.
    SHUTTING_DOWN = 2  # Instance is shutting down.
    TERMINATED = 3  # Instance is terminated.
    STOPPING = 4  # When the stop comment has been received.

    def __init__(self, state):
        """
        Initialize a State object indicating the current state of an instance.
        :param state: Initiger indicating the current state.
        """
        assert 0 <= state <= 4
        super().__init__(state)
