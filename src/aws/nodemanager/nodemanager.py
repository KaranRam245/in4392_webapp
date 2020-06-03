"""
Module for the Node Manager.
"""
from threading import Thread, RLock

from aws.utils.monitor import Listener, Observable, RepeatingHeartBeat
from aws.utils.packets import HeartBeatPacket
from aws.utils.connection import MultiConnectionClient

import aws.utils.connection as con
from aws.utils.state import InstanceState

import time


class TaskPool(Observable):
    """
    The TaskPool accepts the tasks from the user.
    """

    def __init__(self):
        super().__init__()
        self._tasks = []
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self.heart = RepeatingHeartBeat(interval=5, func=self.generate_heartbeat)
        self.heart.start()

    def run(self):
        """
        Start function for the TaskPool.
        """
        while True:
            print('...')
            self.generate_heartbeat()
            time.sleep(15)

    def add_task(self, task):
        """
        Add a new task to the TaskPool.
        :return:
        """
        raise NotImplementedError()

    def generate_heartbeat(self):
        self.notify(
            message=HeartBeatPacket(state=self._instance_state))


class TaskPoolMonitor(Listener, MultiConnectionClient):

    def __init__(self, taskpool, host, port):
        self._lock = RLock()
        self._tp = taskpool
        super().__init__(host, port)

    def event(self, message):
        self.send_message(message)
        self._send_buffer()

    def process_command(self, command):
        print("Need help with command: {}".format(command))


def start_instance(host, port=con.PORT):
    """
    Function to start the Node Scheduler, which is the heart of the Instance Manager.
    """
    taskpool = TaskPool()
    monitor = TaskPoolMonitor(taskpool, host, port)
    taskpool.add_listener(monitor)

    taskpool.run()


if __name__ == "__main__":
    start_instance('localhost', 8080)
