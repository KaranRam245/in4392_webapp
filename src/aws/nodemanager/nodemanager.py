"""
Module for the Node Manager.
"""
import asyncio

import logging
from aws_logging_handlers.S3 import S3Handler
import aws.utils.connection as con
import aws.utils.config as config
from aws.utils.monitor import Listener, Observable
from aws.utils.packets import HeartBeatPacket, CommandPacket, Packet
from aws.utils.state import InstanceState
from aws.utils.logger import Logger


class TaskPool(Observable):
    """
    The TaskPool accepts the tasks from the user.
    """

    def __init__(self, instance_id):
        super().__init__()
        self._tasks = []
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self._instance_id = instance_id
        logger = Logger()

    async def run(self):
        """
        Start function for the TaskPool.
        """
        try:
            while True:
                self.generate_heartbeat()
                await asyncio.sleep(config.HEART_BEAT_INTERVAL)
        except KeyboardInterrupt:
            pass

    def add_task(self, task):
        """
        Add a new task to the TaskPool.
        :return:
        """
        raise NotImplementedError()

    def generate_heartbeat(self, notify=True) -> HeartBeatPacket:
        heartbeat = HeartBeatPacket(instance_id=self._instance_id,
                                    instance_type='node_manager',
                                    instance_state=self._instance_state)
        if notify:
            self.notify(message=heartbeat)
        return heartbeat


class TaskPoolClientWrapper(con.MultiConnectionClient):
    """
    This class is used as a wrapper for the client which connects to the IM.
    """

    def process_command(self, command):
        print("Need help with command: {}".format(command))


class TaskPoolServerWrapper(con.MultiConnectionServer):
    """
    This class is the server for which workers can connect to.
    """

    def __init__(self, host, port, client):
        self.client = client
        super().__init__(host, port)

    def process_heartbeat(self, hb, source) -> Packet:
        hb['source'] = source  # Set the source IP of the heartbeat (i.e., the worker).
        self.client.send_message(hb)  # Forward the heartbeat to IM.
        return hb  # This value is returned to the worker client.

    def process_command(self, command: CommandPacket):
        print("A client send me a command: {}".format(command))


class TaskPoolMonitor(Listener):

    def __init__(self, taskpool, client, server):
        self._tp = taskpool
        self.client = client
        self.server = server
        logger = Logger()
        super().__init__()

    def event(self, message):
        logger.log_info("taskpoolmonitor", "Message sent to Instance Manager: " + message + ".")
        self.client.send_message(message)  # Send message to IM.


def start_instance(instance_id, im_host, nm_host=con.HOST, im_port=con.PORT_IM,
                   nm_port=con.PORT_NM):
    """
    Function to start the TaskPool, which is the heart of the Node Manager.
    """
    logger = Logger()
    logger.log_info("nodemanager_" + instance_id, "Starting TaskPool with ID: " + instance_id + ".")
    taskpool = TaskPool(instance_id=instance_id)
    taskpool_client = TaskPoolClientWrapper(im_host, im_port)
    taskpool_server = TaskPoolServerWrapper(nm_host, nm_port, taskpool_client)
    logger.log_info("nodemanager_" + instance_id, "Starting TaskPoolMonitor of TaskPool with ID: " + instance_id + ".")
    monitor = TaskPoolMonitor(taskpool, taskpool_client, taskpool_server)
    taskpool.add_listener(monitor)

    loop = asyncio.get_event_loop()
    server_core = asyncio.start_server(taskpool_server.run, nm_host, nm_port, loop=loop)

    procs = asyncio.wait([server_core, taskpool.run(), monitor.client.run()])
    tasks = loop.run_until_complete(procs)

    server_socket = None
    for task in tasks:
        if task._result:
            server_socket = task._result.sockets[0]
            break
    if server_socket:
        print('Serving on {}'.format(server_socket.getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    tasks.close()
    loop.run_until_complete(tasks.wait_closed())
    loop.close()


if __name__ == "__main__":
    start_instance('localhost', 8080)
