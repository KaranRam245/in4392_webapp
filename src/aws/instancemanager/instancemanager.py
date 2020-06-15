"""
Module for the Instance Manager.
"""
import asyncio
import time
import traceback
from contextlib import suppress
from time import time

import boto3
from ec2_metadata import ec2_metadata

import aws.utils.config as config
import aws.utils.connection as con
from aws.resourcemanager.resourcemanager import log_metric, log_info, log_warning, log_error, \
    log_exception, ResourceManagerCore
from aws.utils.botoutils import BotoInstanceReader
from aws.utils.packets import Packet, HeartBeatPacket
from aws.utils.state import InstanceState


class Instances:
    NAMES = ('node_manager', 'workers')

    # Instance example:
    # <instance_id>:  <InstanceState>

    def __init__(self):
        self._node_managers = {}
        self._workers = {}
        self._last_heartbeat = {}
        self._start_signal = {}
        self.ip_addresses = {}
        self.charge_time = {'instance_manager': time()}

    def get_all(self, instance_type, filter_state=None):
        """
        Get all instances of a specific type.
        :param instance_type: Instance type you want the instances of.
        :param filter_state: State you would like to filter for.
        :return:
        """
        nodes = self.get_nodes(instance_type)
        if filter_state:
            if isinstance(filter_state, int):
                filter_state = [filter_state]
            nodes = [key for (key, value) in nodes.items() if value.is_any(filter_state)]
        return nodes

    def get_nodes(self, instance_type):
        if instance_type == 'node_manager':
            return self._node_managers
        return self._workers

    def is_state(self, instance_id, instance_type: str, state: int):
        instance: InstanceState = self.get_nodes(instance_type).get(instance_id, None)
        if not instance:
            return False
        return instance.is_state(state)

    def set_state(self, instance_id, instance_type, state: InstanceState):
        nodes = self.get_nodes(instance_type)
        nodes[instance_id] = state
        log_info("State of instance " + instance_id + " set to " + str(state) + ".")

    def set_ip(self, instance_id, ip_address):
        log_info("IP address of " + instance_id + " set to " + ip_address + ".")
        self.ip_addresses[instance_id] = ip_address

    def get_ip(self, instance_id):
        return self.ip_addresses.get(instance_id)

    def has(self, instance_type, filter_state):
        """
        Check if there is an instance type with a specific state.
        :param instance_type: Check for this specific instance type.
        :param filter_state: Check for the specified state in instances.
        :return: Boolean indicating if such an instance is found.
        """
        return len(
            self.get_all(instance_type=instance_type, filter_state=filter_state)) > 0

    def has_instance_not_running(self, instance_type):
        """
        Check if there are instances that are not yet, or not anymore, in a running state.
        :param instance_type: Instance type to check.
        :return: Boolean indicating if there is an instance PENDING, STOPPING, or STOPPED.
        """
        return self.has(instance_type,
                        [InstanceState.PENDING, InstanceState.STOPPING, InstanceState.STOPPED])

    def update_instance_state(self, instance_id, instance_type, boto_response):
        for boto_instance in boto_response:
            if boto_instance.instance_id == instance_id:
                self.set_state(instance_id=instance_id, instance_type=instance_type,
                               state=boto_instance.state)

    def update_instance_all(self, boto_response):
        for boto_instance in boto_response:
            self.set_state(instance_id=boto_instance.instance_id, instance_type=boto_instance.name,
                           state=boto_instance.state)
            self.set_ip(instance_id=boto_instance.instance_id, ip_address=boto_instance.public_ip)

    def get_worker_split(self):
        """
        Get a tuple of (1) workers PENDING or RUNNING and (2) workers STOPPING or STOPPED.
        :return: Tuple of workers that are ON and workers that are OFF.
        """
        workers_on = self.get_all('worker', [InstanceState.RUNNING])
        workers_off = self.get_all('worker', [InstanceState.STOPPED])
        workers_transition = self.get_all('worker', [InstanceState.PENDING, InstanceState.STOPPING])
        return workers_on, workers_off, workers_transition

    def is_type(self, instance_id, instance_type):
        nodes = self.get_nodes(instance_type)
        return instance_id in nodes

    def __str__(self):
        return "All instances:\n" \
               "  node_managers: {}" \
               "  workers: {}".format(str(self._node_managers), str(self._workers))

    def get_last_heartbeat(self, instance_id):
        return self._last_heartbeat.get(instance_id, None)

    def set_last_heartbeat(self, heartbeat):
        instance_id = heartbeat['instance_id']
        self._last_heartbeat[instance_id] = heartbeat['time']

    @staticmethod
    def heart_beat_timedout(heartbeat_time):
        if not heartbeat_time:
            return True
        return (time() - heartbeat_time) >= config.HEART_BEAT_TIMEOUT

    def start_signal_timedout(self, instance_id):
        signal_time = self._start_signal.get(instance_id, None)
        current_time = time()
        diff = current_time - signal_time if signal_time else 999
        log_info('Instance: {}, Last signal_time:{}, time:{}, subtract:{}, {}. sent: {}'.format(
            instance_id,
            signal_time,
            current_time,
            diff,
            diff >= config.START_SIGNAL_TIMEOUT,
            self._start_signal))
        if not signal_time:
            return True
        return (current_time - signal_time) >= config.START_SIGNAL_TIMEOUT

    def set_last_start_signal(self, instance_id):
        """

        :param instance_id:
        """
        self._start_signal[instance_id] = time()

    def clear_time(self, instance_id):
        self._last_heartbeat.pop(instance_id, None)
        self._start_signal.pop(instance_id, None)


class NodeScheduler:
    """
    The main class of the Instance Manager, responsible for the life-time of other instances.
    """

    def __init__(self, debug, git_pull, account_id):
        self.instance_id = ec2_metadata.instance_id
        self.instances = Instances()
        self.ipv4 = ec2_metadata.public_ipv4
        self.dns = ec2_metadata.public_hostname
        self.boto = BotoInstanceReader()
        self.commands = []
        self.cleaned_up = False
        self.debug = debug  # Boolean indicating if the debug mode is enabled.
        self.git_pull = git_pull  # String indicating if workers should first git pull and checkout.
        self.node_manager_running = False
        self.timewindow = TimeWindow()
        self.workers = 0
        self.account_id = account_id
        super().__init__()

    def initialize_nodes(self, retry=False):
        """
        Initialize all required nodes.
        """
        if not retry:  # If debug is enabled, retries may be done. A sync is then not needed.
            self.update_instances(check=False)
        if self.debug and not self.node_manager_running:
            log_info("Debugging waiting for node manager to start running.")
            return False
        log_info("Initializing nodes..")
        if self.instances.has_instance_not_running(instance_type='node_manager'):
            log_info("No node manager running. Initializing startup protocol..")
            self.start_node_manager()  # Start the node manager if not already done.
            self.node_manager_running = True
        if self.instances.has_instance_not_running(instance_type='worker'):
            log_info("No single worker running. Initializing startup protocol..")
            self.start_worker()  # Require at least one worker.
        return True

    def _send_start_command(self, instance_type, instance_id):
        try:
            command = [config.DEFAULT_DIRECTORY,
                       config.DEFAULT_MAIN_CALL.format(instance_type, self.ipv4, instance_id,
                                                       self.account_id)]
            if instance_type == 'worker':
                node_manager_ids = self.instances.get_all('node_manager', InstanceState.RUNNING)
                # If there are more node managers, one could use a smarter method to divide workers.
                command[1] += ' {}'.format(self.instances.get_ip(node_manager_ids[0]))
            if self.git_pull:
                command.insert(1, 'git pull')
                command.insert(2, 'git checkout {}'.format(self.git_pull))
            log_info("Sending start command: [{}]: {}.".format(instance_id, command))
            response = self.boto.ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName='AWS-RunShellScript',
                Parameters={'commands': [' ; '.join(command)]}
            )
            self.commands.append(response['Command']['CommandId'])
            self.instances.set_last_start_signal(instance_id)
        except self.boto.ssm.exceptions.InvalidInstanceId:
            log_info("Instance {} [{}] not yet running. Retry later.".format(instance_type, instance_id))
        except Exception as exc:
            log_exception("The following exception has occurred while trying"
                          + " to send a command: " + str(exc))

    def start_node_manager(self):
        if not self.instances.has('node_manager', [InstanceState.RUNNING, InstanceState.PENDING]):
            nodemanagers = self.instances.get_all(instance_type='node_manager',
                                                  filter_state=[InstanceState.STOPPED])
            if not nodemanagers:
                log_error("No node manager instances available to start.")
                raise ConnectionError('No node manager instances available to start.')
            to_start = nodemanagers[0]
            log_info("Initializing node manager.")
            self._init_instance(to_start, instance_type='node_manager', wait=True)
            self._send_start_command('node_manager', to_start)

    def start_worker(self):
        workers = self.boto.read_ids(self.instance_id, filters=['is_worker', ('is_running', False)])
        if not workers:
            log_info("No more worker instances can be started.")
            return None
        log_info("Initializing worker.")
        self._init_instance(workers[0], instance_type='workers', wait=False)
        return workers[0]

    def _init_instance(self, instance_id, instance_type: str, wait=False):
        log_info("Starting {} instance {}".format(instance_type, instance_id))
        self.boto.ec2.start_instances(InstanceIds=[instance_id])
        if wait:
            waiter = self.boto.ec2.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])
            self.instances.set_state(instance_id, instance_type,
                                     InstanceState(InstanceState.RUNNING))
        else:
            self.instances.set_state(instance_id, instance_type,
                                     InstanceState(InstanceState.PENDING))
        self.instances.charge_time[instance_id] = time()
        log_info("Charge_time: {}".format(self.instances.charge_time))
        if instance_type == 'worker':
            self.workers += 1
            log_metric({'workers': self.workers})

    def _kill_instance(self, instance_ids, instance_types):
        """
        Kill a single instance of a list of instances.
        :param instance_ids: List of instance_ids or a single instance_id.
        :param instance_types: The types of the instance_ids being killed. Or None if not needed.
        """
        if isinstance(instance_ids, str):
            instance_ids = [instance_ids]  # If not already a list, convert to a single-item list.
        self.boto.ec2.stop_instances(InstanceIds=instance_ids)
        if instance_types:
            if isinstance(instance_types, str):
                instance_types = instance_types * len(instance_ids)
            for idx, instance_id in enumerate(instance_ids):
                self.instances.set_state(instance_id, instance_types[idx],
                                         InstanceState(InstanceState.STOPPING))
                self.instances.clear_time(instance_id)
        for idx, instance_id in enumerate(instance_ids):
            if instance_id in self.instances.charge_time:
                log_metric(
                    {'charged_time': {'instance_id': instance_id,
                                      'charged': time() - self.instances.charge_time[instance_id]}})
                del self.instances.charge_time[instance_id]
            else:
                log_warning("No charge_time available for {}".format(instance_id))
            if instance_types and instance_types[idx] == 'worker':
                self.workers -= 1
                log_metric({'workers': self.workers})

    def running_instances(self):
        """
        Get all running instances.
        :return: All instances that have a RUNNING state.
        """
        node_managers = self.instances.get_all('node_manager',
                                               filter_state=[InstanceState.RUNNING])
        workers = self.instances.get_all('worker', filter_state=[InstanceState.RUNNING])
        return node_managers + workers

    def update_instances(self, check=True):
        states = [InstanceState.PENDING, InstanceState.STOPPING]
        if check and not (
                self.instances.has('worker', states) or self.instances.has('node_manager', states)):
            return
        log_info("Updated instance states from AWS state.")
        boto_response = self.boto.read(self.instance_id)
        self.instances.update_instance_all(boto_response=boto_response)
        log_info(str(self.instances))

    async def run(self):
        log_info("Running NodeScheduler..")
        sleep_time = config.SERVER_SLEEP_TIME
        update_counter = config.BOTO_UPDATE_SEC
        try:
            initialized = self.initialize_nodes()
            while self.debug and not initialized:
                log_warning(
                    "Debug enabled and no node manager started yet. "
                    "Waiting {} seconds to retry.".format(config.DEBUG_INIT_RETRY))
                await asyncio.sleep(config.DEBUG_INIT_RETRY)
                initialized = self.initialize_nodes(retry=True)

            while True:
                # Update the Instance states.
                if update_counter <= 0:
                    self.update_instances()
                    update_counter = config.BOTO_UPDATE_SEC

                self.check_all_living()

                # Check if some worker is underloaded or overloaded.
                underloaded = self.timewindow.get_underloaded()
                overloaded = self.timewindow.get_overloaded()
                log_info("Overloaded: {}, Underloaded: {}".format(overloaded, underloaded))
                if underloaded:
                    if overloaded:
                        pass  # The workload should be balanced. IM should do nothing.
                    else:
                        # Kill an underloaded worker. There is not enough work.
                        self._kill_instance(underloaded[0], instance_types=['worker'])
                else:
                    if overloaded:
                        # We need a new worker. There is too much work.
                        worker_id = self.start_worker()
                        self.timewindow.add_empty(worker_id)
                    else:
                        pass  # Everything is doing fine! Do nothing.

                update_counter -= sleep_time
                await asyncio.sleep(sleep_time)
        except KeyboardInterrupt:
            self.cancel_all()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            log_error("The following exception {}"
                      " occured during run: {}".format(exc, traceback.print_exc()))

    def check_all_living(self):
        """
        Check for all node managers and all workers if they are still alive.
        """
        for instance_type in ('node_manager', 'worker'):
            for instance in self.instances.get_nodes(instance_type):
                self._check_living(instance, instance_type)

    def _check_living(self, instance, instance_type):
        """
        Check for an instance if it is still alive or if it should receive a new start command.
        :param instance: Instance id that is checked.
        :param instance_type: Type of the instance being checked.
        """
        if not (self.instances.is_state(instance, instance_type, state=InstanceState.RUNNING) or
                self.instances.is_state(instance, instance_type, state=InstanceState.PENDING)):
            return  # Instances that are not running, should be started elsewhere.
        heartbeat = self.instances.get_last_heartbeat(instance)
        heartbeat_timedout = self.instances.heart_beat_timedout(heartbeat)
        if heartbeat and not heartbeat_timedout:
            self.instances.set_state(instance_id=instance, instance_type=instance_type,
                                     state=InstanceState(InstanceState.RUNNING))
            return  # The instance is perfectly fine.
        if not heartbeat and self.instances.start_signal_timedout(instance):
            # No start signal is sent, or it takes too long to start.
            log_info("No start/timedout signal sent to {}".format(instance))
            log_info("Sent start command to instance {}".format(instance))
            self._send_start_command(instance_type=instance_type, instance_id=instance)
        elif heartbeat:
            # The IM has not received a heartbeat for too long.
            log_error("No/timedout heartbeat recorded "
                      "for instance {}: {}".format(instance,
                                                   self.instances.get_last_heartbeat(instance)))
            log_metric(
                {'charged_time': {'instance_id': instance,
                                  'charged': time() - self.instances.charge_time[instance]}})
            del self.instances.charge_time[instance]
            if instance_type == 'worker':
                self.workers -= 1
                log_metric({'workers': self.workers})
            self._init_instance(instance_id=instance, instance_type=instance_type)

    def cancel_all(self):
        """
        Cancel all running tasks and kill all instances.
        When the debug mode is enabled, the node manager is not killed.
        """
        if self.debug:
            running_instances = self.running_instances()
            running_instances = [kill for kill in running_instances if
                                 self.instances.is_type(kill, 'worker')]
        else:
            running_instances = self.running_instances()
        if running_instances:
            log_info("Killing all instances: {}".format(running_instances))
            self._kill_instance(running_instances, instance_types={})

        log_info("Cancelling all commands..")
        for command in self.commands:
            self.boto.ssm.cancel_command(CommandId=command)
        self.cleaned_up = True


class NodeMonitor(con.MultiConnectionServer):
    """
    Monitor for the Instance Manager.
    """

    def __init__(self, nodescheduler, host=con.HOST, port=con.PORT_IM):
        self._ns = nodescheduler
        self.keep_running = True
        super().__init__(host, port)

    def process_heartbeat(self, heartbeat, source) -> Packet:
        self._ns.instances.set_last_heartbeat(heartbeat=heartbeat)
        if heartbeat['instance_type'] == 'node_manager':
            self._ns.node_manager_running = True
            self._ns.timewindow.update_node_manager(nm_heartbeat=heartbeat)
            return self._generate_nm_response(heartbeat)
        elif heartbeat['instance_type'] == 'worker':
            self._ns.timewindow.update_worker(worker_heartbeat=heartbeat)
            return heartbeat

    def _generate_nm_response(self, heartbeat):
        workers_running = self._ns.instances.get_all('worker', filter_state=[InstanceState.RUNNING])
        workers_pending = self._ns.instances.get_all('worker', filter_state=[InstanceState.PENDING])
        response = HeartBeatPacket(instance_id=heartbeat['instance_id'],
                                   instance_state=InstanceState.RUNNING,
                                   instance_type='instance_manager',
                                   workers_running=workers_running,
                                   workers_pending=workers_pending)
        log_metric({'im_heartbeat': HeartBeatPacket(instance_id='instance_manager',
                                                    instance_state=InstanceState.RUNNING,
                                                    instance_type='instance_manager')})
        return response


class TimeWindow:
    """
    Time window class for keeping track of metrics for overload and underload of workers.
    """

    def __init__(self):
        self.cpu_window = {}
        self.mem_window = {}
        self.queue_window = {}
        self.nm_task_window = {
            'tasks_waiting': 0,
            'tasks_running': 0
        }

    def update_node_manager(self, nm_heartbeat: HeartBeatPacket):
        """
        Update the state of the node manager in the time window.
        :param nm_heartbeat: The heartbeat from the Node manager.
        """
        self.nm_task_window = {
            'tasks_waiting': nm_heartbeat['tasks_waiting'],
            'tasks_running': nm_heartbeat['tasks_running']
        }

    def update_worker(self, worker_heartbeat: HeartBeatPacket):
        """
        Update the worker in the windows. The windows keep track of the last metrics, such as CPU.
        :param worker_heartbeat: Heartbeat received belonging to the worker.
        """
        metric = ('cpu_usage', 'mem_usage', 'queue_size')
        for idx, window in enumerate((self.cpu_window, self.mem_window, self.queue_window)):
            old_window = window.get(worker_heartbeat['instance_id'], None)
            current_metric = worker_heartbeat[metric[idx]]
            if old_window:
                # Add the current metric at the end and shift by removing the first element if
                # The window has has exceeded (i.e.,
                new_window = (old_window + [current_metric])[
                             max(len(old_window) - (config.WINDOW_SIZE - 1), 0):(
                                     config.WINDOW_SIZE + 1)]
                window[worker_heartbeat['instance_id']] = new_window
            else:
                window[worker_heartbeat['instance_id']] = [current_metric]

    def get_overloaded(self, sort=False) -> list:
        """
        Get a list of overloaded workers.
        :param sort: Boolean indicating if the workers should be sorted on the number of jobs.
        :return: List of overloaded workers.
        """
        overloaded = []
        jobs_running = []
        if not self.nm_task_window['tasks_running']:
            return []  # If there are no tasks running, there cannot be an overloaded worker.
        for instance in self.cpu_window:
            if sum(self.cpu_window[instance]) >= config.CPU_OVERLOAD_PRODUCT or \
                    sum(self.mem_window[instance]) >= config.MEM_OVERLOAD_PRODUCT or \
                    self._queue_overloaded(instance):
                overloaded.append(instance)
                jobs_running.append(self.queue_window)
        if sort:
            overloaded, _ = (list(t) for t in zip(*sorted(zip(overloaded, jobs_running))))
        return overloaded

    def get_underloaded(self) -> list:
        """
        Get a list of underloaded workers. Currently, workers without a job.
        :return: List of underloaded workers.
        """
        underloaded = []
        if self.nm_task_window['tasks_waiting']:
            return []  # There are tasks that need to be divided before one can be underloaded.
        for instance in self.queue_window:
            if len(self.queue_window[instance]) > 0 and sum(self.queue_window[instance]) == 0:
                underloaded.append(instance)
        return underloaded

    def add_empty(self, instance_id):
        """
        Add an empty worker to the time window. This worker likely hasn't started yet.
        :param instance_id: Instance id of the worker added.
        """
        self.queue_window[instance_id] = []
        self.mem_window = []
        self.cpu_window = []

    def _queue_overloaded(self, instance):
        """
        Check if the queue of a worker is overloaded. If there are no measurements yet, the
        worker cannot be overloaded yet.
        :param instance: Instance id of the checked worker.
        :return: Boolean indicating if the worker is overloaded.
        """
        window_size = len(self.queue_window[instance])
        if window_size == 0:  # No measurements yet. Likely it is still starting.
            return False
        return sum(self.queue_window[instance]) / window_size >= config.MAX_JOBS_PER_WORKER


def start_instance(debug=False, git_pull=False):
    """
    Function to start the Node Scheduler, which is the heart of the Instance Manager.
    """
    client = boto3.client("sts")
    account_id = client.get_caller_identity()["Account"]
    resource_manager = ResourceManagerCore(account_id=account_id, instance_id='instance_manager')
    log_info("Starting Node Scheduler..")
    scheduler = NodeScheduler(debug=debug, git_pull=git_pull, account_id=account_id)
    monitor = NodeMonitor(scheduler)

    loop = asyncio.get_event_loop()
    server_core = asyncio.start_server(monitor.run, con.HOST, con.PORT_IM, loop=loop)

    procs = asyncio.wait([server_core, scheduler.run(), resource_manager.period_upload_log()])

    try:
        loop.run_until_complete(procs)

        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if not scheduler.cleaned_up:
            scheduler.cancel_all()
        tasks = [t for t in asyncio.Task.all_tasks() if t is not
                 asyncio.Task.current_task()]
        for task in tasks:
            task.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(task)
        resource_manager.upload_log(clean=True)  # Clean the last logs.
        loop.close()


# Main function to start the InstanceManager
if __name__ == '__main__':
    start_instance()
