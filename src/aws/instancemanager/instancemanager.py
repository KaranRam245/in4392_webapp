"""
Module for the Instance Manager.
"""
import asyncio
import time

from ec2_metadata import ec2_metadata

import aws.utils.connection as con
from aws.utils.botoutils import BotoInstanceReader
from aws.utils.packets import Packet
from aws.utils.state import InstanceState
import aws.utils.config as config


class Instances:
    NAMES = ('node_manager', 'workers')

    # Instance example:
    # <instance_id>:  <InstanceState>

    def __init__(self):
        self._node_managers = {}
        self._workers = {}
        self._last_heartbeat = {}
        self._start_signal = {}

    def get_all(self, instance_type, filter_state=None):
        """
        Get all instances of a specific type.
        :param instance_type: Instance type you want the instances of.
        :param filter_state: State you would like to filter for.
        :return:
        """
        nodes = self.get_nodes(instance_type)
        if filter_state:
            if isinstance(filter_state, int):
                filter_state = [filter_state]
            nodes = [node for node in nodes if node.state in filter_state]
        return nodes

    def get_nodes(self, instance_type):
        if instance_type == 'node_manager':
            return self._node_managers
        return self._workers

    def is_state(self, instance_id, instance_type: str, state: int):
        instance = self.get_nodes(instance_type).get(instance_id, None)
        if not instance:
            return False
        return instance == state

    def set_state(self, instance_id, instance_type, state):
        nodes = self.get_nodes(instance_type)
        if instance_id not in nodes:
            nodes[instance_id] = InstanceState(InstanceState.PENDING)
        nodes[instance_id] = state

    def has(self, instance_type, filter_state):
        """
        Check if there is an instance type with a specific state.
        :param instance_type: Check for this specific instance type.
        :param filter_state: Check for the specified state in instances.
        :return: Boolean indicating if such an instance is found.
        """
        return len(
            self.get_all(instance_type, filter_state=filter_state)) > 0

    def has_instance_not_running(self, instance_type):
        """
        Check if there are instances that are not yet, or not anymore, in a running state.
        :param instance_type: Instance type to check.
        :return: Boolean indicating if there is an instance PENDING, STOPPING, or STOPPED.
        """
        return self.has(instance_type, InstanceState.PENDING) or \
               self.has(instance_type, InstanceState.STOPPING) or \
               self.has(instance_type, InstanceState.STOPPED)

    def update_instance_state(self, instance_id, instance_type, boto_response):
        for boto_instance in boto_response:
            if boto_instance.instance_id == instance_id:
                self.set_state(instance_id=instance_id, instance_type=instance_type,
                               state=InstanceState(boto_instance.state))

    def update_instance_all(self, boto_response):
        for boto_instance in boto_response:
            self.set_state(instance_id=boto_instance.instance_id, instance_type=boto_instance.name,
                           state=InstanceState(boto_instance.state))

    def get_worker_split(self):
        """
        Get a tuple of (1) workers PENDING or RUNNING and (2) workers STOPPING or STOPPED.
        :return: Tuple of workers that are ON and workers that are OFF.
        """
        workers_on = self.get_all('worker', [InstanceState.PENDING, InstanceState.RUNNING])
        workers_off = self.get_all('worker', [InstanceState.STOPPING, InstanceState.STOPPED])
        return workers_on, workers_off

    def __str__(self):
        return "All instances:\n" \
               "  node_managers: {}" \
               "  workers: {}".format(str(self._node_managers), str(self._workers))

    def get_last_heartbeat(self, instance_id):
        return self._last_heartbeat.get(instance_id, None)

    def set_last_hearbeat(self, instance_id, heart_beat_time):
        self._last_heartbeat[instance_id] = heart_beat_time

    def start_signal_timedout(self, instance_id, timeout):
        current_time_sec = round(time.time())
        signal_time = self._start_signal.get(instance_id, None)
        if not signal_time:
            return True
        return (current_time_sec - signal_time) >= timeout

    def set_last_start_signal(self, instance_id):
        self._start_signal[instance_id] = round(time.time())

    def clear_time(self, instance_id):
        self._last_heartbeat.pop(instance_id, None)
        self._start_signal.pop(instance_id, None)


class NodeScheduler:
    """
    The main class of the Instance Manager, responsible for the life-time of other instances.
    """

    def __init__(self):
        self.instances = Instances()
        self.instance_id = ec2_metadata.instance_id
        self.ipv4 = ec2_metadata.public_ipv4
        self.dns = ec2_metadata.public_hostname
        self.boto = BotoInstanceReader()
        super().__init__()

    def initialize_nodes(self):
        """
        Initialize all required nodes.
        """
        if not self.instances.has_instance_not_running(instance_type='node_manager'):
            self.start_node_manager()  # Start the node manager if not already done.
        if not self.instances.has_instance_not_running(instance_type='worker'):
            self.start_worker()  # Require at least one worker.

    def _send_start_command(self, instance_type, instance_id):
        self.boto.ec2.run_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': 'python3 in4392_webapp/main.py {} {} {}'.format(
                instance_type, self.ipv4, instance_id)})
        self.instances.set_last_start_signal(instance_id)

    def start_node_manager(self):
        nodemanagers = self.boto.read_ids(self.instance_id, filters=['is_node_manager',
                                                                     ('is_running', False)])
        if not nodemanagers:
            raise ConnectionError('No node manager instances found with the given filters.')
        self._init_instance(nodemanagers[0], instance_type='node_manager', wait=True)
        self._send_start_command('node_manager', nodemanagers[0])

    def start_worker(self):
        workers = self.boto.read_ids(self.instance_id, filters=['is_worker', ('is_running', False)])
        if not workers:
            print('No more worker instances can be started.')
            return
        self._init_instance(workers[0], instance_type='workers', wait=False)

    def _init_instance(self, instance_id: int, instance_type: str, wait=False):
        instance = self.boto.ec2.Instance(id=instance_id)
        if wait:
            instance.wait_until_running()
            self.instances.set_state(instance_id, instance_type,
                                     InstanceState(InstanceState.RUNNING))
        else:
            instance.start()
            self.instances.set_state(instance_id, instance_type,
                                     InstanceState(InstanceState.PENDING))

    def _kill_instance(self, instance_id, instance_type):
        self.boto.ec2.Instance(id=instance_id).stop()
        self.instances.set_state(instance_id, instance_type, InstanceState(InstanceState.STOPPING))
        self.instances.clear_time(instance_id)

    def running_instances(self):
        """
        Get all running instances.
        :return: All instances that have a RUNNING state.
        """
        return self.boto.read_ids(self.instance_id, filters=['is_running'])

    async def run(self):
        print("Running NodeScheduler..")
        sleep_time = 1
        update_counter = config.BOTO_UPDATE_SEC
        try:
            while True:
                # Update the Instance states.
                if update_counter <= 0:
                    boto_response = self.boto.read(self.instance_id)
                    self.instances.update_instance_all(boto_response=boto_response)
                    update_counter = config.BOTO_UPDATE_SEC
                    print(self.instances)
                workers_on, workers_off = self.instances.get_worker_split()

                for worker in workers_on:
                    self._check_script_running(worker)

                # TODO: Do other stuff like keeping track of heartbeats etc.
                # TODO: Create workers when more needed
                # TODO: Kill workers if not needed anymore.

                update_counter -= sleep_time
                await asyncio.sleep(sleep_time)
        except KeyboardInterrupt:
            pass

    def _check_script_running(self, worker):
        if self.instances.get_last_heartbeat(worker):
            return
        if not self.instances.is_state(worker, 'worker', state=InstanceState.RUNNING):
            return
        if self.instances.start_signal_timedout(worker, timeout=config.START_SIGNAL_TIMEOUT):
            self._send_start_command('worker', worker)


class NodeMonitor(con.MultiConnectionServer):

    def __init__(self, nodescheduler, host=con.HOST, port=con.PORT):
        self._ns = nodescheduler
        self.keep_running = True
        super().__init__(host, port)

    def process_heartbeat(self, heartbeat, source) -> Packet:
        print('Received Heartbeat: {}, from: {}'.format(heartbeat, source))
        self._ns.instances.set_last_hearbeat(heartbeat)
        return heartbeat
        # TODO different processing heartbeat. Action if needed.


def start_instance():
    """
    Function to start the Node Scheduler, which is the heart of the Instance Manager.
    """
    scheduler = NodeScheduler()
    monitor = NodeMonitor(scheduler)

    loop = asyncio.get_event_loop()
    server_core = asyncio.start_server(monitor.run, con.HOST, con.PORT, loop=loop)

    procs = asyncio.wait([server_core, scheduler.run()])
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


# Main function to start the InstanceManager
if __name__ == '__main__':
    start_instance()
