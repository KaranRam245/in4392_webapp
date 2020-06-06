"""
Module for the Node Manager.
"""
import asyncio

import aws.utils.connection as con
from aws.utils.monitor import Listener, Observable
from aws.utils.packets import HeartBeatPacket, CommandPacket, Packet
from aws.utils.state import InstanceState


class TaskPool(Observable):
    """
    The TaskPool accepts the tasks from the user.
    """

    def __init__(self):
        super().__init__()
        self._tasks = []
        self._instance_state = InstanceState(InstanceState.RUNNING)

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
            message=HeartBeatPacket(instance_state=self._instance_state,
                                    instance_type='node_manager'))


class TaskPoolClientWrapper(con.MultiConnectionClient):

    def process_command(self, command):
        print("Need help with command: {}".format(command))


class TaskPoolServerWrapper(con.MultiConnectionServer):

    def __init__(self, host, port):
        self.client = None
        super().__init__(host, port)

    def process_heartbeat(self, hb, source) -> Packet:
        hb['source'] = source
        self.client.send_message(hb)
        return hb

    def process_command(self, command: CommandPacket):
        print("A client send me a command: {}".format(command))


class TaskPoolMonitor(Listener):

    def __init__(self, taskpool, client, server):
        self._tp = taskpool
        self.client = client
        server.client = client
        self.server = server
        super().__init__()

    def event(self, message):
        self.client.send_message(message)


def start_instance(host, port=con.PORT):
    """
    Function to start the Node Scheduler, which is the heart of the Instance Manager.
    """
    taskpool = TaskPool()
    taskpool_client = TaskPoolClientWrapper(host, port)
    taskpool_server = TaskPoolServerWrapper(host, port)
    monitor = TaskPoolMonitor(taskpool, taskpool_client, taskpool_server)
    taskpool.add_listener(monitor)

    loop = asyncio.get_event_loop()
    server_core = asyncio.start_server(taskpool_server.run, host, port, loop=loop)

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
