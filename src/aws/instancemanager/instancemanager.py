"""
Module for the Instance Manager.
"""
from aws.utils.botoutils import BotoInstanceReader
from ec2_metadata import ec2_metadata
from aws.utils.connection import Server, Client
from threading import Thread, RLock

import aws.utils.connection as con
import socket
import boto3
import json

from aws.utils.monitor import Buffer
from aws.utils.packets import HeartBeatPacket


class NodeScheduler:
    """
    The main class of the Instance Manager, responsible for the life-time of other instances.
    """

    def __init__(self):
        self.instances = []
        self.ec2 = boto3.client('ec2')
        self.instance_id = ec2_metadata.instance_id
        super().__init__()

    def start_node_manager(self):
        nodemanagers = BotoInstanceReader.read_ids(self.ec2, self.instance_id,
                                                   filters=['is_node_manager',
                                                            ('is_running', False)])
        to_start = nodemanagers[0]
        # TODO: Smarter method to decide which to start.
        self._init_instance(to_start, cmd='nodemanager.py')

    def start_worker(self):
        workers = BotoInstanceReader.read_ids(self.ec2, self.instance_id,
                                              filters=['is_worker', ('is_running', False)])
        to_start = workers[0]
        self._init_instance(to_start, cmd='nodeworker.py')

    def start_resource_manager(self):
        resourcemanagers = BotoInstanceReader.read_ids(self.ec2, self.instance_id,
                                                       filters=['is_resource_manager',
                                                                ('is_running', False)])
        to_start = resourcemanagers[0]
        self._init_instance(to_start, cmd='resourcemanager.py')

    def initialize_nodes(self):
        self.start_node_manager()

    def _init_instance(self, instance: int, cmd):
        if instance:
            print('No instances specified to start.')
            return
        self.ec2.start_instances(InstanceIds=[instance])
        self.instances.append(instance)
        self.notify("Started instance and now pending {}.".format(instance))

    def _kill_instance(self):
        pass

    def running_instances(self):
        """
        Get all running instances.
        """
        return BotoInstanceReader.read_ids(self.ec2, self.instance_id, filters=['is_running'])


class NodeMonitor(Thread):

    def __init__(self, nodescheduler):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((con.HOST, con.PORT))
        self._lock = RLock()
        self._buffer = Buffer()
        self._ns = nodescheduler

    def run(self) -> None:
        while True:
            data, address = self._socket.recvfrom(1024)
            json_data = json.loads(data)
            print(data)
            self._buffer.put(self._lock, HeartBeatPacket(**json_data), address)


def start_instance():
    """
    Function to start the Node Scheduler, which is the heart of the Instance Manager.
    """
    scheduler = NodeScheduler()

    monitor = NodeMonitor(scheduler)
    monitor.run()


# Main function to start the InstanceManager
if __name__ == '__main__':
    start_instance()
