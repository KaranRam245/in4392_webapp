"""
Module for the Node Manager.
"""
import asyncio
import os

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

    def __init__(self, instance_id, host, port):
        Observable.__init__(self)
        con.MultiConnectionServer.__init__(self, host, port)
        self._tasks = []  # Available tasks.
        self._tasks_running = []  # Tasks running.
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self._instance_id = instance_id
        self.workers_running = []
        self.workers_pending = []

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
        log_metric({'tasks_waiting': heartbeat['tasks_waiting'],
                    'tasks_running': heartbeat['tasks_running'],
                    'tasks_total': heartbeat['tasks_waiting'] + heartbeat['tasks_running']})
        # TODO fix the above tasks_waiting and tasks_running with the actual numbers!

        if notify:
            self.notify(message=heartbeat)

    def process_heartbeat(self, hb, source) -> Packet:
        hb['source'] = source  # Set the source IP of the heartbeat (i.e., the worker).
        self.notify(hb)  # Forward the heartbeat to the monitor for metrics.
        if len(self._tasks)>0:  #If there are tasks in the taskpool send a new command to the worker
            packet=CommandPacket(command="task")
            current_task=self._tasks.pop(0)
            packet["task_data"]= current_task.get_task_data()
            current_task.state=TaskState.RUNNING
            self._running_tasks.append(current_task)
            return packet
        else:
            return hb #In case there are no more commands send hb           
        # TODO: process the heartbeat and take actions which task to send where @Karan.
        # In the heartbeat you could indicate how far the job is, if it is done, etc.
        # Based on this task 'state', you could assign new tasks, check if a new task should be
        # assigned to the worker, if a task should be stolen from the worker, etc.

        # This value is returned to the worker client.

    def process_command(self, command: CommandPacket):
        if command["command"]=="done":
            
            if len(self._tasks)>0:  #If there are tasks in the taskpool send a new command to the worker
                packet=CommandPacket(command="task")
                current_task=self._tasks.pop(0)
                packet["task_data"]= current_task.get_task_data()
                current_task.state=TaskState.RUNNING
                self._running_tasks.append(current_task)
                return packet



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
        log_info("Message sent to Instance Manager: {}".format(message))

    def process_command(self, command) -> Packet:
        log_warning(
            "TaskPoolMonitor received a command {}. "
            "This should not happen!".format(command))
        return command

    def process_heartbeat(self, heartbeat: HeartBeatPacket):
        if heartbeat['instance_type'] == 'instance_manager':
            workers_stopped = [worker for worker in
                               self._tp.workers_running if
                               worker not in heartbeat['workers_running']]
            # TODO do something with the workers_stopped. These workers were running before. @Karan.
            self._tp.workers_running = heartbeat['workers_running']
            self._tp.workers_pending = heartbeat['workers_pending']
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
    taskpool = TaskPool(instance_id=instance_id, host=nm_host, port=nm_port)
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
