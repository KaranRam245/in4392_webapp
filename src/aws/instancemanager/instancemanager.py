"""
Module for the Instance Manager.
"""
from aws.utils.monitor import Observable, Listener
from random import randint


class NodeScheduler(Observable):
    """
    The main class of the Instance Manager, responsible for the life-time of other instances.
    """

    def run(self):
        """
        Run function for starting the NodeScheduler.
        """
        while True:
            if randint(0, 100) == 1:
                self.notify(self.__dict__)


class NodeMonitor(Listener):

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format.
        """
        print(message)
        raise NotImplementedError("The class is a listener but has not implemented the event "
                                  "method.")


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
