"""
Module for the Instance Manager.
"""
import asyncio
import time
import traceback
from contextlib import suppress
from time import time
from collections import deque

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
        old_state = nodes.get(instance_id, None)
        if not old_state or not state.is_state(old_state):
            nodes[instance_id] = state
            log_info(
                "State of instance {} set from {} to {}.".format(instance_id, old_state, state))

    def set_ip(self, instance_id, ip_address):
        log_info("IP address of {} set to {}.".format(instance_id, ip_address))
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
        return "All instances:" \
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
                command.insert(1, 'git fetch --all')
                command.insert(2, 'git checkout {}'.format(self.git_pull))
                command.insert(3, 'git pull')
            log_info("Sending start command: [{}]: {}.".format(instance_id, command))
            self.instances.set_last_start_signal(instance_id)
            response = self.boto.ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName='AWS-RunShellScript',
                Parameters={'commands': [' ; '.join(command)]}
            )
            self.commands.append(response['Command']['CommandId'])
        except self.boto.ssm.exceptions.InvalidInstanceId:
            log_info(
                "Instance {} [{}] not yet running. Retry later.".format(instance_type, instance_id))
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
        self._init_instance(workers[0], instance_type='worker', wait=False)
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
        else:
            log_warning(
                "No instance_types specified for {}. Could not properly kill.".format(instance_ids))
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
                active_workers = len(self.instances.get_all('worker',
                                                            filter_state=[InstanceState.PENDING,
                                                                          InstanceState.RUNNING]))
                max_workers = len(self.instances.get_nodes('worker'))
                window_response = self.timewindow.get_action(current_workers=active_workers,
                                                             max_workers=max_workers)
                if 'create' in window_response:
                    self.start_worker()
                elif 'kill' in window_response:
                    self._kill_instance(instance_ids=[window_response['kill']],
                                        instance_types=['worker'])

                update_counter -= sleep_time
                await asyncio.sleep(sleep_time)
        except KeyboardInterrupt:
            self.cancel_all()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            log_error("The following exception {}"
                      " occurred during run: {}".format(exc, traceback.format_exc()))

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
            log_info("Cancelled command: {}".format(command))
        self.cleaned_up = True


class NodeMonitor(con.MultiConnectionServer):
    """
    Monitor for the Instance Manager.
    """

    def __init__(self, nodescheduler, host=con.HOST, port=con.PORT_IM):
        self._ns = nodescheduler
        super().__init__(host, port)

    def process_command(self, command, source) -> Packet:
        log_warning("IM received a command {} from {}. "
                    "This should not happen!".format(command, source))
        return command  # The IM should not receive commands.

    def process_heartbeat(self, heartbeat, source) -> Packet:
        try:
            self._ns.instances.set_last_heartbeat(heartbeat=heartbeat)
            log_metric({'heartbeat': heartbeat})
            if heartbeat['instance_type'] == 'node_manager':
                self._ns.node_manager_running = True
                self._ns.timewindow.update_node_manager(nm_heartbeat=heartbeat)
                log_metric({'tasks_waiting': heartbeat['tasks_waiting'],
                            'tasks_running': heartbeat['tasks_running'],
                            'tasks_total': heartbeat['tasks_waiting'] + heartbeat['tasks_running'],
                            'worker_allocation': heartbeat['worker_allocation']})
                return self._generate_nm_response()
            if heartbeat['instance_type'] == 'worker':
                return heartbeat
            log_warning("Received a heartbeat from an instance type I do not know: {}".format(heartbeat))
            return heartbeat
        except Exception as exc:
            log_error("Error on process_heartbeat {}: {}".format(exc, traceback.format_exc()))
            raise exc

    def _generate_nm_response(self):
        workers_running = self._ns.instances.get_all('worker',
                                                     filter_state=[InstanceState.RUNNING])
        workers_pending = self._ns.instances.get_all('worker',
                                                     filter_state=[InstanceState.PENDING])
        response = HeartBeatPacket(instance_id='instance_manager',
                                   instance_state=InstanceState(InstanceState.RUNNING),
                                   instance_type='instance_manager',
                                   workers_running=workers_running,
                                   workers_pending=workers_pending)
        log_metric({'heartbeat':
                        HeartBeatPacket(instance_id='instance_manager',
                                        instance_state=InstanceState(InstanceState.RUNNING),
                                        instance_type='instance_manager')})
        return response


class TimeWindow:
    """
    Time window class for keeping track of metrics for overload and underload of workers.
    """

    def __init__(self):
        self.mean_total_tasks = deque()
        self.worker_allocation = {}

    def update_node_manager(self, nm_heartbeat: HeartBeatPacket):
        """
        Update the state of the node manager in the time window.
        :param nm_heartbeat: The heartbeat from the Node manager.
        """
        num_workers = len(nm_heartbeat['worker_allocation'])
        if num_workers > 0:
            self.mean_total_tasks.append(
                (nm_heartbeat['tasks_waiting'] + nm_heartbeat['tasks_running']) / num_workers)
        else:
            self.mean_total_tasks.append(0)
        self.worker_allocation = nm_heartbeat['worker_allocation']
        if len(self.mean_total_tasks) > config.WINDOW_SIZE:
            self.mean_total_tasks.popleft()

    def get_action(self, current_workers: int, max_workers: int):
        number_of_workers = len(self.worker_allocation)
        if not self.mean_total_tasks:  # We first need a heartbeat from the Node manager.
            return {}
        if self.mean_total_tasks[-1] > 0 and number_of_workers == 0:
            log_info("[LB] There was no worker, but there is work to do.")
            return {'create': 1}  # There was no worker, but there is work to do.

        mean_task_per_worker = self._mean(self.mean_total_tasks)

        # Check if there are underloaded workers.
        if config.MIN_JOBS_PER_WORKER > mean_task_per_worker:
            if self.mean_total_tasks[-1] > 0 and number_of_workers == 1:
                return {}  # If there is still work and only one worker to do it.
            if current_workers < number_of_workers:
                return {}  # In an earlier check, an instance was already killed wait for next HB.
            # Kill the instance with the least tasks.
            log_info("[LB] The instance with the least tasks will be killed.")
            return {'kill': min(self.worker_allocation, key=self.worker_allocation.get)}

        # Check if there are overloaded workers.
        if mean_task_per_worker > config.MAX_JOBS_PER_WORKER:
            if current_workers == max_workers:
                return {}  # No new worker can be created, if we already reached the limit.
            if current_workers > number_of_workers:
                return {}  # In an earlier check, an instance was already created wait for next HB.
            # Create an instance.
            log_info("[LB] A new instance is needed for load balancing.")
            return {'create': 1}
        return {}

    @staticmethod
    def _mean(values, rounding=2):
        return round(sum(values) / len(values), rounding)


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
        resource_manager.upload_log(clean=False)  # Make sure everything is logged before shutdown.
        if not scheduler.cleaned_up:
            scheduler.cancel_all()
        tasks = asyncio.Task.all_tasks(loop=loop)
        for task in tasks:
            task.cancel()
            log_info("Cancelled task {}".format(task))
        with suppress(asyncio.CancelledError):
            group = asyncio.gather(*tasks, return_exceptions=True)
            loop.run_until_complete(group)
        resource_manager.upload_log(clean=True)  # Clean the last logs.
        loop.close()


# Main function to start the InstanceManager
if __name__ == '__main__':
    start_instance()
