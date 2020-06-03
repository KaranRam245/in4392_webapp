"""
Module for the Instance Manager.
"""
from concurrent.futures import ThreadPoolExecutor
from time import sleep

from ec2_metadata import ec2_metadata

import aws.utils.connection as con
from aws.utils.botoutils import BotoInstanceReader
from aws.utils.monitor import Buffer
from aws.utils.state import InstanceState


class Instances:
    NAMES = ('node_managers', 'resource_managers', 'workers')

    def __init__(self):
        self._node_managers = {}
        self._resource_managers = {}
        self._workers = {}

    def get_all(self, instance_type, state=None):
        if instance_type == 'node_managers':
            nodes = self._node_managers
        elif instance_type == 'resource_managers':
            nodes = self._resource_managers
        else:
            nodes = self._workers
        if state:
            nodes = [inst_id for inst_id in nodes.keys() if state in nodes.values()]
        return nodes

    def set_state(self, instance_id, instance_type, state: InstanceState):
        if instance_type == 'node_managers':
            self._node_managers[instance_id] = state
        elif instance_type == 'resource_managers':
            self._resource_managers[instance_id] = state
        else:
            self._workers[instance_id] = state

    def has(self, instance_type, state):
        """
        Check if there is an instance type with a specific state.
        :param instance_type: Check for this specific instance type.
        :param state: Check for the specified state in instances.
        :return: Boolean indicating if such an instance is found.
        """
        return len(self.get_all(instance_type, state)) > 0

    def has_non_running(self, instance_type):
        """
        Check if there are instances that are not yet, or not anymore, in a running state.
        :param instance_type: Instance type to check.
        :return: Boolean indicating if there is an instance PENDING, STOPPING, or STOPPED.
        """
        return self.has(instance_type, InstanceState.PENDING) or \
               self.has(instance_type, InstanceState.STOPPING) or \
               self.has(instance_type, InstanceState.STOPPED)

    def update_state(self, instance_id, instance_type, boto_response):
        for boto_instance in boto_response:
            if boto_instance.instance_id == instance_id:
                self.set_state(instance_id=instance_id, instance_type=instance_type,
                               state=InstanceState(boto_instance.state))

    def update_all(self, boto_response):
        for boto_instance in boto_response:
            self.set_state(instance_id=boto_instance.instance_id, instance_type=boto_instance.name,
                           state=InstanceState(boto_instance.state))

    def __str__(self):
        return "All instances:\n" \
               "  node_managers: {}" \
               "  resource_managers: {}" \
               "  workers: {}".format(str(self._node_managers), str(self._resource_managers),
                                      str(self._workers))


class NodeScheduler:
    """
    The main class of the Instance Manager, responsible for the life-time of other instances.
    """

    def __init__(self):
        self.instances = Instances()
        self.instance_id = ec2_metadata.instance_id
        self.ipv4 = ec2_metadata.public_ipv4
        self.dns = ec2_metadata.public_hostname
        super().__init__()

    def initialize_nodes(self):
        """
        Initialize all required nodes.
        """
        if not self.instances.has('node_managers', InstanceState.RUNNING):
            self.start_node_manager()
        self._send_start_command('node_manager')
        # if not self.instances.has('resource_managers', InstanceState.RUNNING):
        #     self.start_resource_manager()
        # if not self.instances.has('workers', InstanceState.RUNNING):
        #     self.start_worker()

    def _send_start_command(self, instance_type):
        BotoInstanceReader.EC2.run_command(
            InstanceIds=self.instances.get_all(instance_type, state=InstanceState.RUNNING),
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': 'python3 in4392_webapp/main.py {} {}'.format(
                instance_type, self.ipv4)})

    def start_node_manager(self):
        nodemanagers = BotoInstanceReader.read_ids(self.instance_id,
                                                   filters=['is_node_manager',
                                                            ('is_running', False)])
        to_start = nodemanagers[0]  # TODO: Smarter method to decide which to start.
        if not nodemanagers:
            print('No node manager instances found with the given filters.')
            return
        self._init_instance(to_start, instance_type='node_managers', wait=True)

    def start_worker(self):
        workers = BotoInstanceReader.read_ids(self.instance_id,
                                              filters=['is_worker', ('is_running', False)])
        if not workers:
            print('No worker instances found with the given filters.')
            return
        to_start = workers[0]  # TODO: Smarter method to decide which to start.
        self._init_instance(to_start, instance_type='workers', wait=False)

    def start_resource_manager(self):
        resourcemanagers = BotoInstanceReader.read_ids(self.instance_id,
                                                       filters=['is_resource_manager',
                                                                ('is_running', False)])
        if not resourcemanagers:
            print('No resource manager instances found with the given filters.')
            return
        to_start = resourcemanagers[0]  # TODO: Smarter method to decide which to start.
        self._init_instance(to_start, instance_type='resource_managers', wait=True)

    def _init_instance(self, instance_id: int, instance_type: str, wait=False):
        instance = BotoInstanceReader.EC2.Instance(id=instance_id)
        if wait:
            instance.wait_until_running()
            self.instances.set_state(instance_id, instance_type,
                                     InstanceState(InstanceState.RUNNING))
        else:
            instance.start()
            self.instances.set_state(instance_id, instance_type,
                                     InstanceState(InstanceState.PENDING))

    def _kill_instance(self, instance_id, instance_type, wait=False):
        instance = BotoInstanceReader.EC2.Instance(id=instance_id)
        if wait:
            instance.wait_until_stopped()
            self.instances.set_state(instance_id, instance_type,
                                     InstanceState(InstanceState.STOPPED))
        else:
            instance.stop()
            self.instances.set_state(instance_id, instance_type,
                                     InstanceState(InstanceState.STOPPING))

    def running_instances(self):
        """
        Get all running instances.
        :return: All instances that have a RUNNING state.
        """
        return BotoInstanceReader.read_ids(self.instance_id, filters=['is_running'])

    def run(self, lock):
        print("Running NodeScheduler..")
        try:
            while True:
                boto_response = BotoInstanceReader().read(self.instance_id)
                # with lock:
                #    self.instances.update_all(boto_response=boto_response)
                print(self.instances)
                sleep(15)
        except KeyboardInterrupt:
            pass


class NodeMonitor(con.MultiConnectionServer):

    def __init__(self, nodescheduler, host=con.HOST, port=con.PORT):
        self._buffer = Buffer()
        self._ns = nodescheduler
        super().__init__(host, port)

    def process_heartbeat(self, hb, source):
        print('Received Heartbeat: {}, from: {}'.format(hb, source))
        self._buffer.put(hb, source)


def start_instance():
    """
    Function to start the Node Scheduler, which is the heart of the Instance Manager.
    """
    # manager = Manager()
    # lock = manager.RLock()
    scheduler = NodeScheduler()

    monitor = NodeMonitor(scheduler)
    print('Instance manager running..')

    # pool = Pool()
    # procs = [
    #     pool.apply_async(monitor.run, args=(lock,)),
    #     pool.apply_async(scheduler.run, args=(lock,))
    # ]
    # try:
    #     for proc in procs:
    #         proc.get()
    # except KeyboardInterrupt:
    #     print("Manual program interruption initiated..")
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(monitor.run), executor.submit(scheduler.run)]
        for future in futures:
            future.result()


# Main function to start the InstanceManager
if __name__ == '__main__':
    start_instance()
