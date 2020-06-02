"""
Module for the Instance Manager.
"""
from aws.utils.botoutils import BotoInstanceReader
from ec2_metadata import ec2_metadata
from threading import Thread, RLock

import aws.utils.connection as con
import socket
import boto3
import json

from aws.utils.monitor import Buffer
from aws.utils.packets import HeartBeatPacket
from aws.utils.state import InstanceState


class NodeScheduler:
    """
    The main class of the Instance Manager, responsible for the life-time of other instances.
    """

    def __init__(self):
        self.instances = {
            'node_managers': {},
            'resource_managers': {},
            'workers': {}
        }
        self.ec2 = boto3.client('ec2')
        self.instance_id = ec2_metadata.instance_id
        super().__init__()

    def initialize_nodes(self):
        """
        Initialize all required nodes.
        """
        if not self.has('node_managers', InstanceState.RUNNING):
            self.start_node_manager()
        self.ec2.run_command(InstanceIds=self.get('instance_managers', state=InstanceState.RUNNING),
                             DocumentName='AWS-RunShellScript',
                             Parameters={'commands': 'python3 in4392_webapp/main.py node_manager'})
        # if not self.has('resource_managers', InstanceState.RUNNING):
        #     self.start_resource_manager()
        # if not self.has('workers', InstanceState.RUNNING):
        #     self.start_worker()

    def start_node_manager(self):
        nodemanagers = BotoInstanceReader.read_ids(self.ec2, self.instance_id,
                                                   filters=['is_node_manager',
                                                            ('is_running', False)])
        to_start = nodemanagers[0]  # TODO: Smarter method to decide which to start.
        if not nodemanagers:
            print('No node manager instances found with the given filters.')
            return
        self._init_instance(to_start, instance_type='node_managers', wait=True)

    def start_worker(self):
        workers = BotoInstanceReader.read_ids(self.ec2, self.instance_id,
                                              filters=['is_worker', ('is_running', False)])
        if not workers:
            print('No worker instances found with the given filters.')
            return
        to_start = workers[0]  # TODO: Smarter method to decide which to start.
        self._init_instance(to_start, instance_type='workers', wait=False)

    def start_resource_manager(self):
        resourcemanagers = BotoInstanceReader.read_ids(self.ec2, self.instance_id,
                                                       filters=['is_resource_manager',
                                                                ('is_running', False)])
        if not resourcemanagers:
            print('No resource manager instances found with the given filters.')
            return
        to_start = resourcemanagers[0]  # TODO: Smarter method to decide which to start.
        self._init_instance(to_start, instance_type='resource_managers', wait=True)

    def _init_instance(self, instance_id: int, instance_type: str, wait=False):
        instance = self.ec2.Instance(id=instance_id)
        saved_nodes = self.instances[instance_type]
        if wait:
            instance.wait_until_running()
            saved_nodes[instance] = InstanceState(InstanceState.RUNNING)
        else:
            instance.start()
            saved_nodes[instance] = InstanceState(InstanceState.PENDING)

    def _kill_instance(self, instance_id, instance_type=None, wait=False):
        if not instance_type:
            for (key, values) in self.instances.items():
                if instance_id in values:
                    instance_type = key
        instance = self.ec2.Instance(id=instance_id)
        if wait:
            instance.wait_until_stopped()
            instance[instance_type][instance_id] = InstanceState(InstanceState.STOPPED)
        else:
            instance.stop()
            instance[instance_type][instance_id] = InstanceState(InstanceState.STOPPING)

    def running_instances(self):
        """
        Get all running instances.
        :return: All instances that have a RUNNING state.
        """
        return BotoInstanceReader.read_ids(self.ec2, self.instance_id, filters=['is_running'])

    def get(self, instance_type, state=None):
        """
        Get instances that are the given instance type with the given state.
        :param instance_type:
        Instance type is either 'node_managers', 'workers', or 'resource_managers'.
        :param state: InstanceState for which you might want to filter.
        :return: All instance ids that comply to the given filter and instance type.
        """
        instances = self.instances[instance_type]
        if state:
            instances = [inst_id for inst_id in instances.keys() if state in instances.values()]
        else:
            instances = instances.keys()
        return instances

    def has(self, instance_type, state):
        """
        Check if there is an instance type with a specific state.
        :param instance_type: Check for this specific instance type.
        :param state: Check for the specified state in instances.
        :return: Boolean indicating if such an instance is found.
        """
        instances = self.instances[instance_type]
        return state in instances.values()

    def has_non_running(self, instance_type):
        """
        Check if there are instances that are not yet, or not anymore, in a running state.
        :param instance_type: Instance type to check.
        :return: Boolean indicating if there is an instance PENDING, STOPPING, or STOPPED.
        """
        return self.has(instance_type, InstanceState.PENDING) or \
               self.has(instance_type, InstanceState.STOPPING) or \
               self.has(instance_type, InstanceState.STOPPED)


class NodeMonitor(Thread):

    def __init__(self, nodescheduler):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((con.HOST, con.PORT))
        self._lock = RLock()
        self._buffer = Buffer()
        self._ns = nodescheduler
        super().__init__()

    def run(self) -> None:
        try:
            while True:
                data, address = self._socket.recvfrom(1024)
                data = data.decode(con.ENCODING)
                json_data = json.loads(data)
                print(data)
                self._buffer.put(self._lock, HeartBeatPacket(**json_data), address)
        except KeyboardInterrupt:
            self._socket.close()


def start_instance():
    """
    Function to start the Node Scheduler, which is the heart of the Instance Manager.
    """
    print('Starting instance manager..')
    scheduler = NodeScheduler()

    monitor = NodeMonitor(scheduler)
    print('Instance manager running..')
    monitor.run()


# Main function to start the InstanceManager
if __name__ == '__main__':
    start_instance()
