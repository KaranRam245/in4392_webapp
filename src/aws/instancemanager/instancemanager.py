"""
Module for the Instance Manager.
"""


class NodeScheduler:
    """
    The main class of the Instance Manager, responsible for the life-time of other instances.
    """

    def run(self):
        """
        Run function for starting the NodeScheduler.
        """
        raise NotImplementedError()


def start_node_scheduler():
    """
    Function to start the Node Scheduler, which is the heart of the Instance Manager.
    """
    raise NotImplementedError()

# Main function to start the InstanceManager
if __name__ == '__main__':
    start_node_scheduler()