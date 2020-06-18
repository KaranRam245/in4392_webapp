"""
Shared methods for state indication.
"""
from abc import ABC, abstractmethod
from typing import Iterable


class State(ABC):
    """
    Class for the indication of the current state of an instance.
    """

    def __init__(self, state: int):
        self._state = state

    def get_state(self):
        return self._state

    def set_state(self, state):
        self._state = state

    def is_state(self, state) -> bool:
        if isinstance(state, InstanceState):
            return self._state == state.get_state()
        return self._state == state

    def is_any(self, states: Iterable[int]) -> bool:
        return self._state in states

    @abstractmethod
    def map_to_str(self, state_to_map):
        raise NotImplementedError(
            "Map to string method is not implemented yet for {}".format(type(self)))

    def __str__(self):
        return self.map_to_str(self._state)

    def __repr__(self):
        return str(self)


class ProgramState(State):
    # States of the program based on the Amazon Elastic Compute Cloud.
    # Note that this state is different from the EC2 instance state.
    PENDING = 0  # When the instance has been started but has not yet received a task.
    RUNNING = 1  # When computing or managing.
    STOPPING = 2  # When the stop comment has been received.
    ERROR = 3  # When an error has occurred.

    MAPPING = {
        PENDING: 'pending',
        RUNNING: 'running',
        STOPPING: 'stopping',
        ERROR: 'error'
    }

    def __init__(self, state):
        """
        Initialize a State object indicating the current state of a program.
        :param state: Initiger indicating the current state.
        """
        assert 0 <= state <= 4
        super().__init__(state)

    def map_to_str(self, state_to_map):
        if isinstance(state_to_map, str):
            return state_to_map
        return self.MAPPING[state_to_map]


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

    MAPPING = {
        PENDING: 'pending',
        RUNNING: 'running',
        STOPPING: 'stopping',
        STOPPED: 'stopped',
        SHUTTING_DOWN: 'shutting_down',
        TERMINATED: 'terminated'
    }

    def __init__(self, state):
        """
        Initialize a State object indicating the current state of an instance.
        :param state: Initiger indicating the current state.
        """
        if isinstance(state, str):
            state = self.map_to_int(state)
        assert 0 <= state <= 4
        super().__init__(state)

    def map_to_str(self, state_to_map):
        if isinstance(state_to_map, str):
            return state_to_map
        return self.MAPPING[state_to_map]

    def map_to_int(self, state_to_map):
        """
        Map a string response of EC2 to a state id.
        :param state_to_map: State name or number according to EC2.
        :return: State id.
        """
        if isinstance(state_to_map, int):
            return state_to_map
        for key, value in self.MAPPING.items():
            if value == state_to_map:
                return key
        raise Exception(
            "This state does not seem to exist for InstanceState: {}".format(state_to_map))


class TaskState(State):
    '''
    Class for the indication of the current state of a task
    '''
    UPLOADING = 0
    READY = 1
    RUNNING = 2
    DONE = 3

    def __init__(self, state):
        """
        Initialize a State object indicating the current state of a task.
        :param state: Initiger indicating the current state.
        """
        assert 0 <= state <= 3
        super().__init__(state)
