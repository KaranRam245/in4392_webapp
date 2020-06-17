"""
Module for the Node Worker.
"""
import asyncio
import os
import traceback
from collections import deque
from contextlib import suppress

from tensorflow.keras.models import load_model

import aws.utils.config as config
import aws.utils.connection as con
from aws.resourcemanager.resourcemanager import log_info, log_error, ResourceManagerCore
from aws.utils.monitor import Observable, Listener
from aws.utils.packets import CommandPacket, HeartBeatPacket
from aws.utils.state import ProgramState, InstanceState
from data import Tokenize


class WorkerCore(Observable, con.MultiConnectionClient):
    """
    The WorkerCore accepts the task from the Node Manager.
    """

    def __init__(self, host, port, instance_id, storage_connector):
        Observable.__init__(self)
        con.MultiConnectionClient.__init__(self, host=host, port=port)
        self._instance_id = instance_id
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self._program_state = ProgramState(ProgramState.PENDING)
        self.storage_connector: ResourceManagerCore = storage_connector
        self._task_queue = deque()
        self.current_task = None

    def process_command(self, command: CommandPacket):
        # Enqueue for worker here!
        if command['command'] == 'task':
            self._task_queue.append(command)
        # Skip if command == done (this is an acknowledge).

    async def heartbeat(self):
        """
        Start function for the WorkerCore.
        """
        try:
            while True:
                self.generate_heartbeat()
                await asyncio.sleep(config.HEART_BEAT_INTERVAL_WORKER)
        except KeyboardInterrupt:
            pass

    async def process(self):
        """
        Start function for the WorkerCore.

        return:
            np.array
                Binary 1x6 Numpy array containing the results of the prediction i.e. [0,1,1,0,1,1]
        """
        try:
            while True:
                if not self.current_task and self._task_queue:
                    self.current_task = self._task_queue.popleft()

                    # log_info("Downloading File " + self.current_task.file_path + ".")
                    # file = self.storage_connector.download_file(
                    #     file_path=self.current_task.file_path,
                    #     key=self.current_task.key
                    # )
                    # log_info("Downloaded file " + self.current_task.file_path + ".")
                    input_data = self.current_task["task"]["data"]
                    input_sequences = Tokenize.tokenize_text(
                        os.path.join("src", "aws", "nodeworker", "tokenizer_20000.pickle"),
                        input_data)
                    model = load_model(os.path.join("src", "aws", "nodeworker", "Senti.h5"))
                    labels = model.predict(input_sequences)

                    # Send command with completed task, results and instance id completed
                    message = CommandPacket(command="done")
                    message["labels"] = labels
                    message["instance_id"] = self._instance_id
                    message['task'] = self.current_task["task"]

                    self.send_message(message)

                    self.current_task = None
                await asyncio.sleep(1)  # Pause from task processing.
        except KeyboardInterrupt:
            pass
        except Exception as exc:
            log_error("Worker process crashed {}: {}".format(exc, traceback.format_exc()))
            self.storage_connector.upload_log(clean=False)

    def generate_heartbeat(self, notify=True):
        heartbeat = HeartBeatPacket(instance_id=self._instance_id,
                                    instance_type='worker',
                                    instance_state=self._instance_state,
                                    program_state=self._program_state,
                                    queue_size=len(self._task_queue))
        # self.send_message(message=heartbeat)
        if notify:  # Notify to the listeners (i.e., WorkerMonitor).
            self.notify(message=heartbeat)
        self.send_message(heartbeat)  # Send heartbeat to NodeManagerCore.
        # TODO: more metrics on current task. Current task should be added to heartbeat.


class WorkerMonitor(Listener, con.MultiConnectionClient):

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format.
        """
        log_info("Sending message: {}.".format(message))
        self.send_message(message)

    def process_command(self, command: CommandPacket):
        if command['command'] == 'stop':
            log_error("Command 'stop' is not yet implemented.")
            raise NotImplementedError("Client has not yet implemented [stop].")
        if command['command'] == 'kill':
            log_error("Command 'kill' is not yet implemented.")
            raise NotImplementedError("Client has not yet implemented [kill].")
        log_error("Received unknown command: {}.".format(command['command']))


def start_instance(instance_id, host_im, host_nm, account_id, port_im=con.PORT_IM,
                   port_nm=con.PORT_NM):
    storage_connector = ResourceManagerCore(account_id=account_id, instance_id=instance_id)
    log_info("Starting WorkerCore with instance id:" + instance_id + ".")
    worker_core = WorkerCore(host=host_nm,
                             port=port_nm,
                             instance_id=instance_id,
                             storage_connector=storage_connector)
    monitor = WorkerMonitor(host_im, port_im)
    log_info("Starting WorkerMonitor...")
    worker_core.add_listener(monitor)
    storage_connector.add_listener(monitor)

    loop = asyncio.get_event_loop()
    procs = asyncio.wait(
        [worker_core.run(), worker_core.heartbeat(), worker_core.process(), monitor.run(),
         storage_connector.period_upload_log()])
    try:
        loop.run_until_complete(procs)
    except KeyboardInterrupt:
        pass
    finally:
        log_info("Manually shutting down worker.")
        tasks = [t for t in asyncio.Task.all_tasks() if t is not
                 asyncio.Task.current_task()]
        for task in tasks:
            task.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(task)
        storage_connector.upload_log(clean=True)
        loop.close()
