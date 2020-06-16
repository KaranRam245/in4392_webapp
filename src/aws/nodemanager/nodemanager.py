"""
Module for the Node Manager.
"""
import asyncio
import os
from contextlib import suppress

import pandas as pd

import aws.utils.config as config
import aws.utils.connection as con
from aws.resourcemanager.resourcemanager import log_info, log_warning, ResourceManagerCore
from aws.utils.monitor import Listener, Observable
from aws.utils.packets import HeartBeatPacket, CommandPacket, Packet
from aws.utils.state import InstanceState, TaskState


class TaskPool(Observable, con.MultiConnectionServer):
    """
    The TaskPool accepts the tasks from the user.
    """

    def __init__(self, instance_id, host, port):
        Observable.__init__(self)
        con.MultiConnectionServer.__init__(self, host, port)
        self._tasks = []  # Available tasks.
        self._tasks_running = []  # Tasks running.
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self._instance_id = instance_id
        self.available_workers = []

    async def create_full_taskpool(self):
        imported_csv = pd.read_csv(os.path.join("src", "data", "Input.csv"))
        benchmark_tasks = []
        for row in imported_csv.iterrows():
            task = Task(row["Input"], 0)
            time = int(row["Time"])  # Convert time to int.
            benchmark_tasks.append((time, task))
        benchmark_tasks = sorted(benchmark_tasks, key=lambda x: x[0])  # Sort on time.
        current_time = 0
        while benchmark_tasks:  # While there are tasks.
            while benchmark_tasks[0] == current_time:
                time, task = benchmark_tasks.pop(0)
                self._tasks.append(task)  # Append task to the taskpool on given time.
            current_time += 1
            await asyncio.sleep(1)

    async def run_task_pool(self):
        """
        Start function for the TaskPool.
        """
        try:
            while True:
                self.generate_heartbeat()

                # TODO: divide the tasks here. @Karan (see below)
                """
                Send them to workers. The available workers are in 
                self.available_workers. You may need to create a list of divided work where you
                keep track of the divided work and keep track of tasks that are actuall divided
                or still waiting for a heartbeat of a worker to give the task.
                
                in process_heartbeat you can then actuall send the task to the worker with a
                CommandPacket.
                """
                # TODO: process for keeping track of work.
                # Based on a buffer, decisions can be made. Whenever the process_heartbeat comes
                # in from the desired worker, the task can be assigned/stolen.

                await asyncio.sleep(config.HEART_BEAT_INTERVAL_NODE_MANAGER)
        except KeyboardInterrupt:
            pass

    def add_task(self, task):
        """
        Add a new task to the TaskPool.
        :return:
        """
        raise NotImplementedError()

    def generate_heartbeat(self, notify=True):
        """
        Generate a heartbeat that is send to the TaskPoolMonitor.
        :param notify: If notify is true, send to the listeners. Here it should always be true.
        """
        heartbeat = HeartBeatPacket(instance_id=self._instance_id,
                                    instance_type='node_manager',
                                    instance_state=self._instance_state,
                                    tasks_waiting=len(self._tasks),
                                    tasks_running=len(self._tasks_running))
        if notify:
            self.notify(message=heartbeat)

    def process_heartbeat(self, hb, source) -> Packet:
        hb['source'] = source  # Set the source IP of the heartbeat (i.e., the worker).
        self.notify(hb)  # Forward the heartbeat to the monitor for metrics.

        # TODO: process the heartbeat and take actions which task to send where @Karan.

        # TODO: replace the hb below with command packet is work stealing, or new work is assigned.
        return hb  # This value is returned to the worker client.

    def process_command(self, command: CommandPacket):
        return command # TODO: replace this return. This is called when work is completed by worker.


class TaskPoolMonitor(Listener, con.MultiConnectionClient):
    """
    This class is used to monitor the TaskPool and to send heartbeats to the IM.
    """

    def __init__(self, taskpool, host, port, instance_id):
        Listener.__init__(self)
        con.MultiConnectionClient.__init__(self, host, port)
        self._tp = taskpool

    def event(self, message):
        self.send_message(message)  # TODO process heartbeats and send metrics to IM @Sander.
        log_info("Message sent to Instance Manager: ")

    def process_command(self, command):
        log_warning(
            "TaskPoolMonitor received a command {} from {}. "
            "This should not happen!".format(command, source))
        return command

    def process_heartbeat(self, heartbeat: HeartBeatPacket):
        self._tp.available_workers = heartbeat['available_workers']


def start_instance(instance_id, im_host, account_id, nm_host=con.HOST, im_port=con.PORT_IM,
                   nm_port=con.PORT_NM):
    """
    Function to start the TaskPool, which is the heart of the Node Manager.
    """
    log_info("Starting TaskPool with ID: " + instance_id + ".")
    resource_manager = ResourceManagerCore(instance_id=instance_id, account_id=account_id)
    taskpool = TaskPool(instance_id=instance_id, host=nm_host, port=nm_port)
    monitor = TaskPoolMonitor(taskpool=taskpool, host=im_host, port=im_port,
                              instance_id=instance_id)
    taskpool.add_listener(monitor)

    loop = asyncio.get_event_loop()
    server_core = asyncio.start_server(taskpool.run, nm_host, nm_port, loop=loop)

    procs = asyncio.wait([server_core, taskpool.run_task_pool(), monitor.run(),
                          resource_manager.period_upload_log(), taskpool.create_full_taskpool()])
    loop.run_until_complete(procs)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        tasks = [t for t in asyncio.Task.all_tasks() if t is not
                 asyncio.Task.current_task()]
        for task in tasks:
            task.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(task)
        resource_manager.upload_log(clean=True)
        loop.close()


class Task:
    """
    Task contains all information with regards to a tasks in the TaskPool
    """

    TEXT = 0
    CSV = 1

    def __init__(self, data, dataType):
        self.data = data
        self.taskType = dataType
        self.state = TaskState.UPLOADING

    def get_task_type(self):
        return self.taskType

    def get_task_data(self):
        return self.data

    def get_task_state(self):
        return self.state
