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
    PENDING = 0  # When the instance has been started but has not yet received a task.
    RUNNING = 1  # When computing or managing.
    STOPPING = 2  # When the stop comment has been received.
    ERROR = 3  # When an error has occured.

    def __init__(self, state):
        """
        Initialize a State object indicating the current state of a program.
        :param state: Initiger indicating the current state.
        """
        assert 0 <= state <= 4
        super().__init__(state)


class InstanceState(State):
    """
    States of the instance based on the EC2 instance life-cycle states.
    """
    PENDING = 0  # When the instance has been started but has not yet received a task.
    RUNNING = 1  # When computing or managing.
    STOPPING = 2  # When the stop comment has been received.
    STOPPED = 3  # When the instance is stopped.
    SHUTTING_DOWN = 3  # Instance is shutting down/preparing to terminate.
    TERMINATED = 4  # Instance is terminated/permanently deleted.

    def __init__(self, state):
        """
        Initialize a State object indicating the current state of an instance.
        :param state: Initiger indicating the current state.
        """
        if isinstance(state, str):
            state = self.map_to_id(state)
        assert 0 <= state <= 4
        super().__init__(state)

    def map_to_id(self, state_name: str) -> int:
        """
        Map a string response of EC2 to a state id.
        :param state_name: State name according to EC2.
        :return: State id.
        """
        if state_name == 'pending':
            return self.PENDING
        if state_name == 'running':
            return self.RUNNING
        if state_name == 'stopping':
            return self.STOPPING
        if state_name == 'stopped':
            return self.STOPPED
        if state_name == 'shutting-down':
            return self.SHUTTING_DOWN
        if state_name == 'terminated':
            return self.TERMINATED
        raise Exception(
            'Unknown instance detected. EC2 does not support the "{}" state'.format(state_name))

    def __str__(self):
        return str(self._state)
