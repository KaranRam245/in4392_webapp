"""
Module for the Node Manager.
"""
import asyncio
from contextlib import suppress

import aws.utils.connection as con
import aws.utils.config as config
from aws.resourcemanager.resourcemanager import log_info, log_warning, log_metric, \
    ResourceManagerCore
from aws.utils.monitor import Listener, Observable
from aws.utils.packets import HeartBeatPacket, CommandPacket, Packet
from aws.utils.state import InstanceState


class TaskPool(Observable, con.MultiConnectionServer):
    """
    The TaskPool accepts the tasks from the user.
    """

    def __init__(self, instance_id, host, port):
        Observable.__init__(self)
        con.MultiConnectionServer.__init__(self, host, port)
        self._tasks = []
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self._instance_id = instance_id
        self.workers_running = []
        self.workers_pending = []

    async def run_task_pool(self):
        """
        Start function for the TaskPool.
        """
        try:
            while True:
                self.generate_heartbeat()
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
                                    tasks_running=len(self._tasks))
        log_metric({'tasks_waiting': heartbeat['tasks_waiting'],
                    'tasks_running': heartbeat['tasks_running'],
                    'tasks_total': heartbeat['tasks_waiting'] + heartbeat['tasks_running']})
        # TODO fix the above tasks_waiting and tasks_running with the actual numbers!
        if notify:
            self.notify(message=heartbeat)

    def process_heartbeat(self, hb, source) -> Packet:
        hb['source'] = source  # Set the source IP of the heartbeat (i.e., the worker).

        # TODO: process the heartbeat and take actions which task to send where @Karan.
        # In the heartbeat you could indicate how far the job is, if it is done, etc.
        # Based on this task 'state', you could assign new tasks, check if a new task should be
        # assigned to the worker, if a task should be stolen from the worker, etc.

        return hb  # This value is returned to the worker client.

    def process_command(self, command: CommandPacket):
        log_info("A client send me a command: {}".format(command))


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

    def process_command(self, command):
        log_info("Need help with command: {}".format(command))

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
                          resource_manager.period_upload_log()])
    try:
        loop.run_until_complete(procs)

        loop.run_forever()
    except KeyboardInterrupt:
        pass
    except ConnectionRefusedError as exc:
        print("Could not connect to server {}".format(exc))
    finally:
        tasks = [t for t in asyncio.Task.all_tasks() if t is not
                 asyncio.Task.current_task()]
        for task in tasks:
            task.cancel()
            log_info("Cancelled task {}".format(task))
        resource_manager.upload_log(clean=True)
        loop.close()
