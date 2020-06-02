"""
Module for the Node Manager.
"""
from threading import Thread, RLock

from aws.utils.monitor import Listener, Observable, RepeatingHeartBeat
from aws.utils.packets import HeartBeatPacket
from aws.utils.connection import Client

import aws.utils.connection as con
from aws.utils.state import InstanceState

import time


class TaskPool(Observable):
    """
    The TaskPool accepts the tasks from the user.
    """

    def __init__(self):
        self._tasks = []
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self.heart = RepeatingHeartBeat(interval=5, func=self.generate_heartbeat)
        self.heart.start()
        super().__init__()

    def run(self):
        """
        Start function for the TaskPool.
        """
        while True:
            print('...')
            time.sleep(15)

    def add_task(self, task):
        """
        Add a new task to the TaskPool.
        :return:
        """
        raise NotImplementedError()

    def generate_heartbeat(self):
        self.notify(
            message=HeartBeatPacket(state=self._instance_state, cpu_usage=100, mem_usage=50))


class TaskPoolMonitor(Listener):

    def __init__(self, taskpool, host):
        self._lock = RLock()
        self._tp = taskpool
        self.client = Client(host=host)
        super().__init__()

    def event(self, message):
        self.client.send(message)


def start_instance(host=con.HOST):
    """
    Function to start the Node Scheduler, which is the heart of the Instance Manager.
    """
    taskpool = TaskPool()
    monitor = TaskPoolMonitor(taskpool, host)
    taskpool.add_listener(monitor)

    taskpool.run()


if __name__ == "__main__":
    start_instance(host='localhost')
