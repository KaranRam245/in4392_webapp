"""
Module for the Node Worker.
"""
import asyncio
import os
import traceback
from collections import deque
from contextlib import suppress
from time import time

import numpy as np

import aws.utils.config as config
import aws.utils.connection as con
from aws.resourcemanager.resourcemanager import log_info, log_error, ResourceManagerCore
from aws.utils.monitor import Observable, Listener
from aws.utils.packets import CommandPacket, HeartBeatPacket
from aws.utils.state import ProgramState, InstanceState
from data import Tokenize
from models.Senti import Senti


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
        self.args = {}
        self._model = Senti()
        self._model.set_pretrained_embeddings(20000, 100, np.zeros([20000, 100]))
        self._model.build(input_shape=(100, 1))
        log_info("[PROGRESS] Loaded model..")
        self._model.load_weights(os.path.join("src", "aws", "nodeworker", "Senti.h5"))
        self._task_command_received = False

    def process_command(self, command: CommandPacket):
        # Enqueue for worker here!
        if command['command'] == 'task':
            self._task_queue.append(command)
            self._task_command_received = True
        if command['command'] == 'done':
            self._task_command_received = False

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
                    start_time_task = time()
                    self.current_task = self._task_queue.popleft()
                    self._program_state = ProgramState(ProgramState.RUNNING)

                    os.makedirs(config.DEFAULT_JOB_LOCAL_DIRECTORY, exist_ok=True)
                    task_file_name = self.current_task['task']
                    log_info("Downloading File {}.".format(task_file_name))
                    start_time_download = time()
                    filepath = config.DEFAULT_JOB_LOCAL_DIRECTORY + task_file_name
                    self.storage_connector.download_file(
                        file_path=filepath,
                        key=task_file_name,
                        bucket_name=self.storage_connector.files_bucket
                    )
                    time_to_download = round(time() - start_time_download, 5)
                    with open(filepath, 'r') as f:
                        input_data = "".join(f.readlines())
                        log_info("Read downloaded file {}.".format(filepath))

                        input_sequences = Tokenize.tokenize_text(
                            os.path.join("src", "aws", "nodeworker", "tokenizer_20000.pickle"),
                            input_data)
                        labels = self._model.predict(input_sequences)

                        run_time_task = round(time() - start_time_task, 5)
                        # Send command with completed task, results and instance id completed
                        message = CommandPacket(command="done",
                                                argmax=np.argmax(labels),
                                                instance_id=self._instance_id,
                                                task=self.current_task["task"],
                                                task_start=self.current_task['time'],
                                                time_to_download=time_to_download,
                                                run_time_task=run_time_task)

                        log_info("[PROGRESS] Created response {}".format(message))

                        self.send_message(message)

                        self._program_state = ProgramState(ProgramState.PENDING)
                        self.current_task = None
                await asyncio.sleep(1)  # Pause from task processing.
        except KeyboardInterrupt:
            pass
        except Exception as exc:
            self._program_state = ProgramState(ProgramState.ERROR)
            self.args = {'exc': str(exc), 'trace': traceback.format_exc()}
            log_error("Worker process crashed {}: {}".format(exc, traceback.format_exc()))
            self.storage_connector.upload_log(clean=False)

    def generate_heartbeat(self, notify=True):
        heartbeat = HeartBeatPacket(instance_id=self._instance_id,
                                    instance_type='worker',
                                    instance_state=self._instance_state,
                                    program_state=str(self._program_state),
                                    queue_size=len(self._task_queue),
                                    current_task_start=self.current_task['time'] if self.current_task else '',
                                    args=self.args,
                                    no_hb_task=self._task_command_received)
        # self.send_message(message=heartbeat)
        if notify:  # Notify to the listeners (i.e., WorkerMonitor).
            self.notify(message=heartbeat)
        self.send_message(heartbeat)  # Send heartbeat to NodeManagerCore.
        # TODO: more metrics on current task. Current task should be added to heartbeat.


class WorkerMonitor(Listener, con.MultiConnectionClient):

    def __init__(self, host, port, core):
        self.core = core
        Listener.__init__(self)
        con.MultiConnectionClient.__init__(self, host, port)

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format.
        """
        if self.connection_lost:
            message['error_monitor'] = self.last_exception
            message['trace_monitor'] = self.last_trace
        if self.core.connection_lost:
            message['error_core'] = self.core.last_exception
            message['trace_core'] = self.core.last_trace
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
    monitor = WorkerMonitor(host_im, port_im, worker_core)
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
