"""
Module for the Node Worker.
"""
import asyncio

import aws.utils.connection as con
import aws.utils.config as config
from aws.resourcemanager.resourcemanager import ResourceManagerCore
from aws.utils.monitor import Observable, Listener
from aws.utils.packets import CommandPacket, HeartBeatPacket
from aws.utils.state import ProgramState, InstanceState


class WorkerCore(Observable):
    """
    The WorkerCore accepts the task from the Node Manager.
    """

    def __init__(self, instance_id, task_queue, storage_connector):
        super().__init__()
        self._instance_id = instance_id
        self._task_queue = task_queue
        self.current_task = None
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self._program_state = ProgramState(ProgramState.PENDING)
        self.storage_connector = storage_connector

    async def heartbeat(self):
        """
        Start function for the WorkerCore.
        """
        try:
            while True:
                self.generate_heartbeat()
                await asyncio.sleep(config.HEART_BEAT_INTERVAL)
        except KeyboardInterrupt:
            pass

    async def run(self):
        """
        Start function for the WorkerCore.
        """
        try:
            while True:
                if not self.current_task and self._task_queue:
                    self.current_task = self._task_queue.pop(0)
                    file = self.storage_connector.download_file(
                        file_path=self.current_task.file_path,
                        key=self.current_task.key
                    )
                    # TODO: Process the file! @Karan
                    await asyncio.sleep(2)
                    self.current_task = None
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass

    def generate_heartbeat(self, notify=True) -> HeartBeatPacket:
        heartbeat = HeartBeatPacket(instance_id=self._instance_id,
                                    instance_type='worker',
                                    instance_state=self._instance_state,
                                    program_state=self._program_state)
        if notify:
            self.notify(message=heartbeat)
        return heartbeat
        # TODO: more metrics on current task. Current task should be added to heartbeat.


class WorkerMonitor(Listener, con.MultiConnectionClient):

    def __init__(self, host, port, task_queue):
        self._task_queue = task_queue
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
            raise NotImplementedError("Client has not yet implemented [stop].")
        if command['command'] == 'kill':
            raise NotImplementedError("Client has not yet implemented [kill].")
        if command['command'] == 'task':
            self._task_queue.put(command)
        print('Received unknown command: {}'.format(command['command']))


def start_instance(instance_id, host, port=con.PORT):
    task_queue = []
    storage_connector = ResourceManagerCore()
    worker_core = WorkerCore(instance_id=instance_id,
                             task_queue=task_queue,
                             storage_connector=storage_connector)
    monitor = WorkerMonitor(host, port, task_queue)
    worker_core.add_listener(monitor)
    storage_connector.add_listener(monitor)

    loop = asyncio.get_event_loop()
    procs = asyncio.wait([worker_core.run(), worker_core.heartbeat(), monitor.run()])
    try:
        tasks = loop.run_until_complete(procs)
        tasks.close()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(tasks.wait_close())
        loop.close()
