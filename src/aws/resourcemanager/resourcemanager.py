"""
Module for the Resource Manager.
"""
from aws.utils.monitor import Monitor


class TaskPool:

    def __init__(self):
        pass

    def run(self):
        raise NotImplementedError()

    def add_job(self):
        raise NotImplementedError()


class WorkerMonitor(Monitor):

    def __init__(self):
        pass

    def run(self):
        raise NotImplementedError()
