"""
Module for the Instance Manager.
"""
import asyncio
import time
import traceback
from contextlib import suppress

from ec2_metadata import ec2_metadata

import aws.utils.connection as con
from aws.utils.botoutils import BotoInstanceReader
from aws.utils.packets import Packet
from aws.utils.state import InstanceState
import aws.utils.config as config
from aws.resourcemanager.resourcemanager import Logger


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
        self.start_retry = {}
        self.logger = Logger()

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

    def set_state(self, instance_id, instance_type, state):
        nodes = self.get_nodes(instance_type)
        if instance_id not in nodes:
            self.logger.log_info("State of instance " + instance_id + " set to PENDING.")
            nodes[instance_id] = InstanceState(InstanceState.PENDING)
        self.logger.log_info("State of instance " + instance_id + " set to " + str(state) + ".")
        nodes[instance_id] = state

    def set_ip(self, instance_id, ip_address):
        self.logger.log_info("IP address of " + instance_id + " set to " + ip_address + ".")
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
        workers_on = self.get_all('worker', [InstanceState.PENDING, InstanceState.RUNNING])
        workers_off = self.get_all('worker', [InstanceState.STOPPING, InstanceState.STOPPED])
        return workers_on, workers_off

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
        print("Last heartbeats: {}".format(self._last_heartbeat))

    def heart_beat_timedout(self, instance_id):
        heartbeat_time = self.get_last_heartbeat(instance_id)
        if not heartbeat_time:
            return True
        heartbeat_time = round(heartbeat_time)
        current_time_sec = round(time.time())
        return (current_time_sec - heartbeat_time) >= config.HEART_BEAT_TIMEOUT

    def start_signal_timedout(self, instance_id):
        signal_time = self._start_signal.get(instance_id, None)
        if not signal_time:
            return True
        current_time_sec = round(time.time())
        return (current_time_sec - signal_time) >= config.START_SIGNAL_TIMEOUT

    def set_last_start_signal(self, instance_id):
        self._start_signal[instance_id] = round(time.time())

    def clear_time(self, instance_id):
        self._last_heartbeat.pop(instance_id, None)
        self._start_signal.pop(instance_id, None)


class NodeScheduler:
    """
    The main class of the Instance Manager, responsible for the life-time of other instances.
    """

    def __init__(self, debug, git_pull):
        self.instances = Instances()
        self.instance_id = ec2_metadata.instance_id
        self.ipv4 = ec2_metadata.public_ipv4
        self.dns = ec2_metadata.public_hostname
        self.boto = BotoInstanceReader()
        self.commands = []
        self.cleaned_up = False
        self.debug = debug  # Boolean indicating if the debug mode is enabled.
        self.git_pull = git_pull  # String indicating if workers should first git pull and checkout.
        self.node_manager_running = False
        self.logger = Logger()
        super().__init__()

    def initialize_nodes(self, retry=False):
        """
        Initialize all required nodes.
        """
        if not retry:  # If debug is enabled, retries may be done. A sync is then not needed.
            self.update_instances(check=False)
        if self.debug and not self.node_manager_running:
            self.logger.log_info("Debugging waiting for node manager to start running.")
            print("Debugging waiting for node manager to start running.")
            return False
        self.logger.log_info("Initializing nodes..")
        print("Initializing nodes..")
        if self.instances.has_instance_not_running(instance_type='node_manager'):
            self.logger.log_info("No node manager running. Intializing startup protocol..")
            print("No node manager running. Intializing startup protocol..")
            self.start_node_manager()  # Start the node manager if not already done.
            self.node_manager_running = True
        if self.instances.has_instance_not_running(instance_type='worker'):
            self.logger.log_info("No single worker running. Intializing startup protocol..")
            print("No single worker running. Intializing startup protocol..")
            self.start_worker()  # Require at least one worker.
        return True

    def _send_start_command(self, instance_type, instance_id):
        try:
            command = [config.DEFAULT_DIRECTORY,
                       config.DEFAULT_MAIN_CALL.format(instance_type, self.ipv4, instance_id)]
            if instance_type == 'worker':
                node_manager_ids = self.instances.get_all('node_manager', InstanceState.RUNNING)
                # If there are more node managers, one could use a smarter method to divide workers.
                command[1] += ' {}'.format(self.instances.get_ip(node_manager_ids[0]))
            if self.git_pull:
                command.insert(1, 'git pull')
                command.insert(2, 'git checkout {}'.format(self.git_pull))
            self.logger.log_info("Sending start command: [{}]: {}.".format(instance_id, command))
            print("Sending start command: [{}]: {}".format(instance_id, command))
            response = self.boto.ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName='AWS-RunShellScript',
                Parameters={'commands': [' ; '.join(command)]}
            )
            self.commands.append(response['Command']['CommandId'])
            self.instances.set_last_start_signal(instance_id)
        except Exception as e:
            self.logger.log_exception("The following exception has occurred while trying"
            + " to send a command: " + str(e))
            print(Exception, e, "Retry later")
            self.instances.start_retry[instance_id] = config.INSTANCE_START_CONFIGURE_TIMEOUT

    def start_node_manager(self):
        if not self.instances.has('node_manager', [InstanceState.RUNNING, InstanceState.PENDING]):
            nodemanagers = self.instances.get_all(instance_type='node_manager',
                                                  filter_state=[InstanceState.STOPPED])
            if not nodemanagers:
                self.logger.log_error("No node manager instances available to start.")
                raise ConnectionError('No node manager instances available to start.')
            to_start = nodemanagers[0]
            self.logger.log_info("Initializing node manager.")
            self._init_instance(to_start, instance_type='node_manager', wait=True)
            self._send_start_command('node_manager', to_start)

    def start_worker(self):
        workers = self.boto.read_ids(self.instance_id, filters=['is_worker', ('is_running', False)])
        if not workers:
            self.logger.log_info("No more worker instances can be started.")
            print('No more worker instances can be started.')
            return
        self.logger.log_info("Initializing worker.")
        self._init_instance(workers[0], instance_type='workers', wait=False)

    def _init_instance(self, instance_id: int, instance_type: str, wait=False):
        self.logger.log_info("Starting {} instance {}".format(instance_type, instance_id))
        print("Starting {} instance {}".format(instance_type, instance_id))
        self.boto.ec2.start_instances(InstanceIds=[instance_id])
        if wait:
            waiter = self.boto.ec2.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])
            self.instances.set_state(instance_id, instance_type,
                                     InstanceState(InstanceState.RUNNING))
        else:
            self.instances.set_state(instance_id, instance_type,
                                     InstanceState(InstanceState.PENDING))

    def _kill_instance(self, instance_id, instance_type):
        self.boto.ec2.stop_instances(id=[instance_id])
        self.instances.set_state(instance_id, instance_type, InstanceState(InstanceState.STOPPING))
        self.instances.clear_time(instance_id)

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
        self.logger.log_info("Updated instance states from AWS state.")
        print("Updated instance states from AWS state")
        boto_response = self.boto.read(self.instance_id)
        self.instances.update_instance_all(boto_response=boto_response)
        print(self.instances)

    async def run(self):
        self.logger.log_info("Running NodeScheduler..")
        print("Running NodeScheduler..")
        sleep_time = 1
        update_counter = config.BOTO_UPDATE_SEC
        try:
            initialized = self.initialize_nodes()
            while self.debug and not initialized:
                self.logger.log_warning("Debug enabled and no node manager started yet. "
                      "Waiting {} seconds to retry.".format(config.DEBUG_INIT_RETRY))
                print("Debug enabled and no node manager started yet. "
                      "Waiting {} seconds to retry.".format(config.DEBUG_INIT_RETRY))
                await asyncio.sleep(config.DEBUG_INIT_RETRY)
                initialized = self.initialize_nodes(retry=True)

            while True:
                # Update the Instance states.
                if update_counter <= 0:
                    self.update_instances()
                    update_counter = config.BOTO_UPDATE_SEC
                    print(self.instances)

                self.check_all_living()

                # TODO: Create workers when more needed
                # TODO: Kill workers if not needed anymore.

                update_counter -= sleep_time
                await asyncio.sleep(sleep_time)
        except KeyboardInterrupt:
            self.cancel_all()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(Exception, e)
            print(traceback.print_exc())

    def check_all_living(self):
        for instance_type in ('node_manager', 'worker'):
            for instance in self.instances.get_nodes(instance_type):
                self._check_living(instance, instance_type)

    def _check_living(self, instance, instance_type):
        if not self.instances.is_state(instance, instance_type, state=InstanceState.RUNNING):
            return  # Instances that are not running, should be started elsewhere.
        heartbeat = self.instances.get_last_heartbeat(instance)
        heartbeat_timedout = self.instances.heart_beat_timedout(instance)
        if heartbeat and not heartbeat_timedout:
            return  # The instance is perfectly fine.
        send_start = False
        if self.instances.start_signal_timedout(instance):
            # No start signal is sent, or it takes too long to start.
            if instance not in self.instances.start_retry:
                print("No start/timedout signal sent to {}".format(instance))
                send_start = True
            else:
                value = self.instances.start_retry[instance]
                if value > 0:
                    self.instances.start_retry[instance] -= 1
                else:
                    del self.instances.start_retry[instance]
        elif not send_start and heartbeat and heartbeat_timedout:
            # The IM has not received a heartbeat for too long.
            self.logger.log_error("No/timedout heartbeat recorded "
                  "for instance {}: {}".format(instance,
                                               self.instances.get_last_heartbeat(instance)))
            print("No/timedout heartbeat recorded "
                  "for instance {}: {}".format(instance,
                                               self.instances.get_last_heartbeat(instance)))
            send_start = True
        if send_start:  # Send a new start signal to the instance.
            self.logger.log_info("Sent start command to instance {}".format(instance))
            print("Sent start command to instance {}".format(instance))
            self._send_start_command(instance_type=instance_type, instance_id=instance)

    def cancel_all(self):
        if self.debug:
            running_instances = self.running_instances()
            running_instances = [kill for kill in running_instances if
                                 self.instances.is_type(kill, 'worker')]
        else:
            running_instances = self.running_instances()
        if running_instances:
            self.logger.log_info("Killing all instances: {}".format(running_instances))
            print("Killing all instances: {}".format(running_instances))
            self.boto.ec2.stop_instances(InstanceIds=running_instances)

        self.logger.log_info("Cancelling all commands..")
        print("Cancelling all commands..")
        for command in self.commands:
            self.boto.ssm.cancel_command(CommandId=command)
        self.cleaned_up = True


class NodeMonitor(con.MultiConnectionServer):

    def __init__(self, nodescheduler, host=con.HOST, port=con.PORT_IM):
        self._ns = nodescheduler
        self.keep_running = True
        super().__init__(host, port)

    def process_heartbeat(self, heartbeat, source) -> Packet:
        if heartbeat['instance_type'] == 'node_manager':
            self._ns.node_manager_running = True
        self._ns.instances.set_last_heartbeat(heartbeat=heartbeat)
        return heartbeat
        # TODO load-balancing on heartbeats. Action if needed.


def start_instance(debug=False, git_pull=False):
    """
    Function to start the Node Scheduler, which is the heart of the Instance Manager.
    """
    logger = Logger()
    logger.log_info("Starting Node Scheduler..")
    scheduler = NodeScheduler(debug=debug, git_pull=git_pull)
    monitor = NodeMonitor(scheduler)

    loop = asyncio.get_event_loop()
    server_core = asyncio.start_server(monitor.run, con.HOST, con.PORT_IM, loop=loop)

    procs = asyncio.wait([server_core, scheduler.run()])

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
        loop.close()
        logger.close()


# Main function to start the InstanceManager
if __name__ == '__main__':
    start_instance()
