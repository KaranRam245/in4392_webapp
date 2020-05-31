"""
Module for the Instance Manager.
"""
from aws.utils.botoutils import BotoInstanceReader, BotoInstance
from aws.utils.monitor import Observable, Listener

import boto3
from ec2_metadata import ec2_metadata


class NodeScheduler(Observable):
    """
    The main class of the Instance Manager, responsible for the life-time of other instances.
    """

    def __init__(self):
        self.instances = []
        self.ec2 = boto3.client('ec2')
        self.instance_id = ec2_metadata.instance_id
        super().__init__()

    def start_node_manager(self):
        nodemanagers = BotoInstanceReader.read(self.ec2, self.instance_id,
                                               filters=['is_node_manager', ('is_running', False)])
        nodemanager_ids = [manager.instance_id for manager in nodemanagers]
        self._init_instance(nodemanager_ids)  # TODO: Smarter method to decide which to start.

    def start_worker(self):
        workers = BotoInstanceReader.read(self.ec2, self.instance_id,
                                          filters=['is_worker', ('is_running', False)])
        self._init_instance(workers)

    def start_resource_manager(self):
        resourcemanagers = BotoInstanceReader.read(self.ec2, self.instance_id,
                                                   filters=['is_resource_manager',
                                                            ('is_running', False)])
        self._init_instance(resourcemanagers)

    def initialize_nodes(self):
        self.start_node_manager()

    def _init_instance(self, instances):
        if instances:
            print('No instances specified to start.')
            return
        self.ec2.start_instances(InstanceIds=instances)
        self.notify("Started instances and now pending {}.".format(instances))

    def _kill_instance(self):
        pass

    def terminate(self):
        pass

    def run(self):
        """
        Run function for starting the NodeScheduler.
        """
        self.initialize_nodes()

        self.notify(str(self.__dict__))  # TODO better notify function.


class NodeMonitor(Listener):

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a message result.
        :param message: Message of the event.
        """
        if isinstance(message, str):
            print("[INFO] " + message)  # TODO: create logging system.
        else:
            raise NotImplementedError("The class is a listener but has not implemented the event "
                                      "method.")
        # TODO: Create actual monitor.


def start_instance():
    """
    Function to start the Node Scheduler, which is the heart of the Instance Manager.
    """
    scheduler = NodeScheduler()
    monitor = NodeMonitor()
    scheduler.add_listener(monitor)

    scheduler.run()


# Main function to start the InstanceManager
if __name__ == '__main__':
    start_instance()
