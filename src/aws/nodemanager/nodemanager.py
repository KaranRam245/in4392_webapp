"""
Module for the Node Manager.
"""
import asyncio

import aws.utils.connection as con
from aws.utils.connection import MultiConnectionClient
from aws.utils.monitor import Listener, Observable
from aws.utils.heartbeat import RepeatingHeartBeat
from aws.utils.packets import HeartBeatPacket
from aws.utils.state import InstanceState


class TaskPool(Observable):
    """
    The TaskPool accepts the tasks from the user.
    """

    def __init__(self):
        super().__init__()
        self._tasks = []
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self.heart = RepeatingHeartBeat(interval=15, func=self.generate_heartbeat)
        self.heart.start()

    async def run(self):
        """
        Start function for the TaskPool.
        """
        try:
            while True:
                self.generate_heartbeat()
                await asyncio.sleep(15)
        except KeyboardInterrupt:
            pass

    def add_task(self, task):
        """
        Add a new task to the TaskPool.
        :return:
        """
        raise NotImplementedError()

    def generate_heartbeat(self):
        self.notify(
            message=HeartBeatPacket(state=self._instance_state, instance_type='node_manager'))


class TaskPoolMonitor(Listener, MultiConnectionClient):

    def __init__(self, taskpool, host, port):
        self._tp = taskpool
        super().__init__(host, port)

    def event(self, message):
        self.send_message(message)

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
