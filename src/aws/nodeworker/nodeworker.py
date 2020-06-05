"""
Module for the Node Worker.
"""
import asyncio
import aws.utils.connection as con

from aws.utils.connection import MultiConnectionClient
from aws.utils.monitor import Observable, Listener
from aws.utils.packets import CommandPacket


class WorkerCore(Observable):
    """
    The WorkerCore accepts the task from the Node Manager.
    """

    async def run(self):
        """
        Start function for the WorkerCore.
        """
        raise NotImplementedError()


class WorkerMonitor(Listener, MultiConnectionClient):

    def __init__(self, host, port):
        super().__init__(host, port)

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format.
        """
        raise NotImplementedError("The class is a listener but has not implemented the event "
                                  "method.")

    def process_command(self, command: CommandPacket):
        if command['command'] == 'stop':
            self.running = False
        elif command['command'] == 'task':
            raise NotImplementedError("Client has not yet implemented process_command.")
        else:
            print('Received unknown command: {}'.format(command['command']))


def start_instance(host, port=con.PORT):
    worker_core = WorkerCore()
    monitor = WorkerMonitor(host, port)
    worker_core.add_listener(monitor)

    loop = asyncio.get_event_loop()
    procs = asyncio.wait([worker_core.run(), monitor.run()])
    tasks = loop.run_until_complete(procs)

    tasks.close()
    loop.run_until_complete(tasks.wait_close())
    loop.close()
