"""
Module for the Node Manager.
"""
import asyncio
import os
import traceback
from collections import Counter, deque
from time import time
import uuid
import re

import pandas as pd

import aws.utils.config as config
import aws.utils.connection as con
from aws.resourcemanager.resourcemanager import log_info, log_warning, log_metric, \
    log_error, ResourceManagerCore
from aws.utils.monitor import Listener, Observable
from aws.utils.packets import HeartBeatPacket, CommandPacket, Packet
from aws.utils.state import InstanceState, TaskState


class TaskPool(Observable, con.MultiConnectionServer):
    """
    The TaskPool accepts the tasks from the user.
    """

    def __init__(self, instance_id, host, port, resource_manager):
        Observable.__init__(self)
        con.MultiConnectionServer.__init__(self, host, port)
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self._instance_id = instance_id
        self.resource_manager: ResourceManagerCore = resource_manager
        self.tasks = deque()  # Available & Unassigned tasks.
        self.all_assigned_tasks = 0  # Number of tasks which are assigned but not running
        self.task_assignment = {}  # Available & Assigned tasks
        self.task_processing = {}  # Tasks currently being processed
        self._workers_running = []
        self._workers_pending = []

    @staticmethod
    def translate(data):
        return re.sub(r'[\n\r\t"\']+', ' ', data)

    def register_task(self, task_data):
        unique_id_file = str(uuid.uuid4()) + '.txt'
        local_path = config.DEFAULT_JOB_LOCAL_DIRECTORY + unique_id_file
        with open(local_path, 'w+') as f:
            f.write(task_data)
        self.resource_manager.upload_file(
            file_path=local_path,
            key=unique_id_file,
            bucket_name=self.resource_manager.files_bucket
        )
        os.remove(local_path)
        return unique_id_file

    async def create_full_taskpool(self):
        try:
            os.makedirs(config.DEFAULT_JOB_LOCAL_DIRECTORY, exist_ok=True)

            imported_csv = pd.read_csv(os.path.join("src", "data", "Input.csv"))
            benchmark_tasks = [(row.Time, self.translate(row.Input)) for _, row in imported_csv.iterrows()]
            benchmark_tasks = deque(sorted(benchmark_tasks, key=lambda x: x[0]))  # Sort on time.

            current_time = 0
            while benchmark_tasks:  # While there are tasks.
                while benchmark_tasks and benchmark_tasks[0][0] == current_time:
                    _, task_data = benchmark_tasks.popleft()
                    task = self.register_task(task_data)
                    self.tasks.append(task)  # Append task to the taskpool on given time.
                current_time += 1
                await asyncio.sleep(1)
        except Exception as exc:
            log_error("Could not read benchmark file {}: {}".format(exc, traceback.format_exc()))
            raise exc

    async def run_task_pool(self):
        """
        Start function for the TaskPool.
        """
        try:
            while True:
                self.generate_heartbeat()

                while self.tasks:
                    if not (self._workers_running + self._workers_pending):
                        log_info("Currently, there are no workers to give work to.")
                        break  # If there are currently no workers to give work to, wait.
                    task_per_worker = {key: len(value) for key, value in
                                       self.task_assignment.items()}

                    task = self.tasks.popleft()
                    worker = min(task_per_worker, key=task_per_worker.get)
                    self.task_assignment[worker].append(task)
                    self.all_assigned_tasks += 1

                await asyncio.sleep(config.HEART_BEAT_INTERVAL_NODE_MANAGER)
        except KeyboardInterrupt:
            pass

    def steal_task(self, worker):
        """
        Steals a task from the worker with the most number of tasks
        """
        assignments = {key: len(value) for key, value in self.task_assignment.items()}
        victim_worker = max(assignments, key=assignments.get)
        if assignments[victim_worker] >= 2:
            task = self.task_assignment[victim_worker].pop()
            self.task_assignment[worker].append(task)
            return task
        return None

    def worker_change(self, running, pending):
        """
        Based on the new running and pending workers provided by the IM. Finds stopped or
        newly created workers
        """
        previous_workers = self._workers_running + self._workers_pending
        total_current = running + pending
        stopped_workers = [worker for worker in previous_workers if worker not in total_current]
        new_workers = [worker for worker in total_current if worker not in previous_workers]

        self._workers_running = running
        self._workers_pending = pending

        return stopped_workers, new_workers

    def generate_heartbeat(self, notify=True):
        """
        Generate a heartbeat that is send to the TaskPoolMonitor.
        :param notify: If notify is true, send to the listeners. Here it should always be true.
        """
        assignments = Counter({key: len(value) for key, value in self.task_assignment.items()})
        processing = Counter({key: len(value) for key, value in self.task_processing.items()})
        heartbeat = HeartBeatPacket(instance_id=self._instance_id,
                                    instance_type='node_manager',
                                    instance_state=self._instance_state,
                                    tasks_waiting=self.all_assigned_tasks + len(self.tasks),
                                    tasks_running=len(processing),
                                    worker_allocation=dict(assignments + processing))
        log_metric({'tasks_waiting': heartbeat['tasks_waiting'],
                    'tasks_running': heartbeat['tasks_running'],
                    'tasks_total': heartbeat['tasks_waiting'] + heartbeat['tasks_running']})

        if notify:
            self.notify(message=heartbeat)

    def process_heartbeat(self, hb, source) -> Packet:
        # If the worker has an assigned task, but has not started. Give a task from assigned.
        if not hb['no_hb_task'] and hb['instance_id'] in self.task_assignment:
            packet = CommandPacket(command="task")
            assignments = self.task_assignment[hb['instance_id']]
            if assignments:
                packet['task'] = assignments.popleft()
            else:
                stolen_packet = self.steal_task(hb['instance_id'])
                if stolen_packet:
                    packet['task'] = stolen_packet
                else:
                    return hb
            self.task_processing[hb['instance_id']].append(packet['task'])
            return packet

        return hb

    def process_command(self, command: CommandPacket, source):
        if command["command"] == "done":
            self.task_processing[command["instance_id"]].popleft()
            self.all_assigned_tasks -= 1

            log_metric({'task_finished': {'start_time': command['task_start'],
                                          'duration': time() - command['task_start']}})

            packet = CommandPacket(command="task")
            if len(self.task_assignment[command['instance_id']]) > 0:
                # If there are tasks in the taskpool send a new command to the worker
                packet['task'] = self.task_assignment[command['instance_id']].popleft()
                self.task_processing[command['instance_id']].append(packet['task'])
            else:
                stolen_task = self.steal_task(command['instance_id'])
                if stolen_task:
                    self.task_processing[command['instance_id']].append(stolen_task)
                    packet["task"] = stolen_task
                else:
                    return command
            return packet
        return command


class TaskPoolMonitor(Listener, con.MultiConnectionClient):
    """
    This class is used to monitor the TaskPool and to send heartbeats to the IM.
    """

    def __init__(self, taskpool, host, port):
        Listener.__init__(self)
        con.MultiConnectionClient.__init__(self, host, port)
        self._tp = taskpool

    def event(self, message):
        self.send_message(message)

    def process_command(self, command):
        log_warning(
            "TaskPoolMonitor received a command {}. "
            "This should not happen!".format(command))

    def process_heartbeat(self, heartbeat: HeartBeatPacket):
        if heartbeat['instance_type'] == 'instance_manager':
            stopped_workers, new_workers = self._tp.worker_change(
                running=heartbeat['workers_running'],
                pending=heartbeat['workers_pending'])

            # Add all tasks remaining in stopped worker assignments back to the taskpool
            for worker in stopped_workers:
                self._tp.all_assigned_tasks -= len(self._tp.task_assignment[worker])
                self._tp.tasks += self._tp.task_assignment[worker]
                del self._tp.task_assignment[worker]
                del self._tp.task_processing[worker]
            for worker in new_workers:
                self._tp.task_assignment[worker] = deque()
                self._tp.task_processing[worker] = deque()
        else:
            log_warning(
                'I received a heartbeat from {} [{}] '
                'but I do not know what to do with it. HB: {}'.format(
                    heartbeat['instance_type'], heartbeat['instance_id'], heartbeat))


def start_instance(instance_id, im_host, account_id, nm_host=con.HOST, im_port=con.PORT_IM,
                   nm_port=con.PORT_NM):
    """
    Function to start the TaskPool, which is the heart of the Node Manager.
    """

    log_info("Starting TaskPool with ID: " + instance_id + ".")
    resource_manager = ResourceManagerCore(instance_id=instance_id, account_id=account_id)
    taskpool = TaskPool(instance_id=instance_id, host=nm_host, port=nm_port, resource_manager=resource_manager)
    monitor = TaskPoolMonitor(taskpool=taskpool, host=im_host, port=im_port)
    taskpool.add_listener(monitor)

    loop = asyncio.get_event_loop()
    server_core = asyncio.start_server(taskpool.run, nm_host, nm_port, loop=loop)

    procs = asyncio.wait([server_core, taskpool.run_task_pool(), monitor.run(),
                          resource_manager.period_upload_log(), taskpool.create_full_taskpool()])
    loop.run_until_complete(procs)
    try:
        loop.run_until_complete(procs)

        loop.run_forever()
    except KeyboardInterrupt:
        pass
    except ConnectionRefusedError as exc:
        log_error("Could not connect to server {}".format(exc))
    finally:
        tasks = [t for t in asyncio.Task.all_tasks() if t is not
                 asyncio.Task.current_task()]
        for task in tasks:
            task.cancel()
            log_info("Cancelled task {}".format(task))
        resource_manager.upload_log(clean=True)
        loop.close()


class Task(dict):
    """
    Task contains all information with regards to a tasks in the TaskPool
    """

    def __init__(self, data, dataType):
        data = re.sub('\n|\t|\r|\'|"', '', data)
        super().__init__(data=data, taskType=dataType, state=TaskState.UPLOADING)

    def get_task_type(self):
        return self['taskType']

    def get_task_data(self):
        return self['data']

    def get_task_state(self):
        return self['state']
