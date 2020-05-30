"""
Module for the Instance Manager.
"""
from aws.utils.monitor import Observable, Listener

import boto3


class NodeScheduler(Observable):
    """
    The main class of the Instance Manager, responsible for the life-time of other instances.
    """

    def __init__(self):
        self.instances = []
        self.ec2 = boto3.client('ec2')
        super().__init__()

    def start_node_manager(self):
        print(self.ec2.describe_instances())
        self._init_instance()
        pass

    def start_worker(self):
        self._init_instance()
        pass

    def start_resource_manager(self):
        self._init_instance()
        pass

    def initialize_nodes(self):
        self.start_node_manager()
        self.start_resource_manager()

    def _init_instance(self):
        pass

    def _kill_instance(self):
        pass

    def terminate(self):
        pass

    def run(self):
        """
        Run function for starting the NodeScheduler.
        """
        self.initialize_nodes()

        self.notify(self.__dict__) # TODO better notify function.


class NodeMonitor(Listener):

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format.
        """
        print(message)
        # TODO: Create actual monitor.


def start_node_scheduler():
    """
    Function to start the Node Scheduler, which is the heart of the Instance Manager.
    """
    scheduler = NodeScheduler()
    monitor = NodeMonitor()
    scheduler.add_listener(monitor)

    scheduler.run()


# Main function to start the InstanceManager
if __name__ == '__main__':
    start_node_scheduler()
