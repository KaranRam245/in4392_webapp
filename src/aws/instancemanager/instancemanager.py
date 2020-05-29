"""
Module for the Instance Manager.
"""
from abc import ABC

from aws.utils.monitor import Monitor


class NodeScheduler:
    """
    The main class of the Instance Manager, responsible for the life-time of other instances.
    """

    def run(self):
        """
        Run function for starting the NodeScheduler.
        """
        raise NotImplementedError()


class NodeMonitor(Monitor):

    _listeners = []

    def run(self):
        """
        Run the Monitor class.
        """
        raise NotImplementedError()

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format.
        """
        raise NotImplementedError("The class is a listener but has not implemented the event "
                                  "method.")


def start_node_scheduler():
    """
    Function to start the Node Scheduler, which is the heart of the Instance Manager.
    """
    raise NotImplementedError()


# Main function to start the InstanceManager
if __name__ == '__main__':
    start_node_scheduler()
