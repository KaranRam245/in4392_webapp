"""
Shared methods for state indication.
"""
from typing import Iterable


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

    def is_any(self, states: Iterable[int]) -> bool:
        return self._state in states


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
    SHUTTING_DOWN = 4  # Instance is shutting down/preparing to terminate.
    TERMINATED = 5  # Instance is terminated/permanently deleted.

    def __init__(self, state):
        """
        Initialize a State object indicating the current state of an instance.
        :param state: Initiger indicating the current state.
        """
        if isinstance(state, str):
            state = self.map_to(state)
        assert 0 <= state <= 4
        super().__init__(state)

    def map_to(self, state_to_map):
        """
        Map a string response of EC2 to a state id.
        :param state_to_map: State name or number according to EC2.
        :return: State id.
        """
        mapping = {
            self.PENDING: 'pending',
            self.RUNNING: 'running',
            self.STOPPING: 'stopping',
            self.STOPPED: 'stopped',
            self.SHUTTING_DOWN: 'shutting_down',
            self.TERMINATED: 'terminated'
        }
        if isinstance(state_to_map, str):
            for key, value in mapping.items():
                if value == state_to_map:
                    return key
        elif isinstance(state_to_map, int):
            return mapping[state_to_map]
        raise Exception(
            'Unknown instance detected. EC2 does not support the "{}" state with type "{}"'.format(
                state_to_map, type(state_to_map)))

    def __str__(self):
        return self.map_to(self._state)

    def __repr__(self):
        return str(self)
