"""
Module for the Node Worker.
"""
import asyncio
import aws.utils.connection as con

from aws.utils.connection import MultiConnectionClient
from aws.utils.monitor import Observable, Listener
from aws.utils.packets import CommandPacket, HeartBeatPacket
from aws.utils.state import ProgramState, InstanceState


class WorkerCore(Observable):
    """
    The WorkerCore accepts the task from the Node Manager.
    """

    def __init__(self):
        super().__init__()
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self._program_state = ProgramState(ProgramState.PENDING)

    async def run(self):
        """
        Start function for the WorkerCore.
        """
        try:
            while True:
                self.generate_heartbeat()
                await asyncio.sleep(15)
        except KeyboardInterrupt:
            pass

    def generate_heartbeat(self):
        self.notify(message=HeartBeatPacket(instance_state=self._instance_state,
                                            instance_type='worker',
                                            program_state=self._program_state))


class WorkerMonitor(Listener, MultiConnectionClient):

    def __init__(self, host, port):
        super().__init__(host, port)

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format.
        """
        self.send_message(message)

    def process_command(self, command: CommandPacket):
        if command['command'] == 'stop':
            raise NotImplementedError("Client has not yet implemented process_command.")
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
    try:
        tasks = loop.run_until_complete(procs)
        tasks.close()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(tasks.wait_close())
        loop.close()
