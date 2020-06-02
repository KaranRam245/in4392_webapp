"""
Module for the Node Manager.
"""
import json
import socket
from threading import Thread, RLock

from aws.utils.monitor import Listener, Observable
from aws.utils.packets import HeartBeatPacket

import  aws.utils.connection as con
from aws.utils.state import InstanceState


class TaskPool(Thread, Observable):
    """
    The TaskPool accepts the tasks from the user.
    """
    def __init__(self):
        self._tasks = []
        self._instance_state = InstanceState(InstanceState.RUNNING)
        super().__init__()

    def run(self) -> None:
        """
        Start function for the TaskPool.
        """
        self.notify(self.generate_heartbeat())

    def add_task(self, task):
        """
        Add a new task to the TaskPool.
        :return:
        """
        raise NotImplementedError()

    def generate_heartbeat(self):
        return HeartBeatPacket(state=self._instance_state, cpu_usage=100, mem_usage=50)


class TaskPoolMonitor(Listener):

    def __init__(self, taskpool):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((con.HOST, con.PORT))
        self._lock = RLock()
        self._tp = taskpool
        super().__init__()

    def event(self, message):
        if isinstance(message, dict):
            message = str(message)
        else:
            message = json.dumps(message.__dict__)
        self._socket.sendall(message)


def start_instance():
    """
    Function to start the Node Scheduler, which is the heart of the Instance Manager.
    """
    taskpool = TaskPool()
    monitor = TaskPoolMonitor(taskpool)
    taskpool.add_listener(monitor)

    taskpool.run()


if __name__ == "__main__":
    start_instance()
