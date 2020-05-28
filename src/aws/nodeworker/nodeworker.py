"""
Module for the Node Worker.
"""


class WorkerCore:
    """
    The WorkerCore accepts the task from the Node Manager.
    """

    def run(self):
        """
        Start function for the WorkerCore.
        """
        raise NotImplementedError()
