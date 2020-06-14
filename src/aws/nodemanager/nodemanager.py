"""
Module for the Node Manager.
"""
import asyncio
import logging
from contextlib import suppress

import aws.utils.connection as con
import aws.utils.config as config
from aws.resourcemanager.resourcemanager import ResourceManagerCore
from aws.utils.monitor import Listener, Observable
from aws.utils.packets import HeartBeatPacket, CommandPacket, Packet
from aws.utils.state import InstanceState


class TaskPool(Observable, con.MultiConnectionServer):
    """
    The TaskPool accepts the tasks from the user.
    """

    def __init__(self, instance_id, host, port):
        Observable.__init__(self)
        con.MultiConnectionServer.__init__(self, host, port)
        self._tasks = []
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self._instance_id = instance_id

    async def run_task_pool(self):
        """
        Start function for the TaskPool.
        """
        try:
            while True:
                self.generate_heartbeat()
                await asyncio.sleep(config.HEART_BEAT_INTERVAL)
        except KeyboardInterrupt:
            pass

    def add_task(self, task):
        """
        Add a new task to the TaskPool.
        :return:
        """
        raise NotImplementedError()

    def generate_heartbeat(self, notify=True):
        """
        Generate a heartbeat that is send to the TaskPoolMonitor.
        :param notify: If notify is true, send to the listeners. Here it should always be true.
        """
        heartbeat = HeartBeatPacket(instance_id=self._instance_id,
                                    instance_type='node_manager',
                                    instance_state=self._instance_state)
        if notify:
            self.notify(message=heartbeat)

    def process_heartbeat(self, hb, source) -> Packet:
        hb['source'] = source  # Set the source IP of the heartbeat (i.e., the worker).
        self.notify(hb)  # Forward the heartbeat to the monitor for metrics.

        # TODO: process the heartbeat and take actions which task to send where @Karan.

        return hb  # This value is returned to the worker client.

    def process_command(self, command: CommandPacket):
        logging.info("A client send me a command: {}".format(command))


class TaskPoolMonitor(Listener, con.MultiConnectionClient):
    """
    This class is used to monitor the TaskPool and to send heartbeats to the IM.
    """

    def __init__(self, taskpool, host, port, instance_id):
        Listener.__init__(self)
        con.MultiConnectionClient.__init__(self, host, port)
        self._tp = taskpool

    def event(self, message):
        self.send_message(message)  # TODO process heartbeats and send metrics to IM @Sander.
        logging.info("Message sent to Instance Manager: " + str(message))

    def process_command(self, command):
        logging.info("Need help with command: {}".format(command))


def start_instance(instance_id, im_host, account_id, nm_host=con.HOST, im_port=con.PORT_IM,
                   nm_port=con.PORT_NM):
    """
    Function to start the TaskPool, which is the heart of the Node Manager.
    """
    logging.info("Starting TaskPool with ID: " + instance_id + ".")
    resource_manager = ResourceManagerCore(instance_id=instance_id, account_id=account_id)
    taskpool = TaskPool(instance_id=instance_id, host=nm_host, port=nm_port)
    monitor = TaskPoolMonitor(taskpool=taskpool, host=im_host, port=im_port, instance_id=instance_id)
    taskpool.add_listener(monitor)

    loop = asyncio.get_event_loop()
    server_core = asyncio.start_server(taskpool.run, nm_host, nm_port, loop=loop)

    procs = asyncio.wait([server_core, taskpool.run_task_pool(), monitor.run(), resource_manager.period_upload_log()])
    loop.run_until_complete(procs)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        tasks = [t for t in asyncio.Task.all_tasks() if t is not
                 asyncio.Task.current_task()]
        for task in tasks:
            task.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(task)
        resource_manager.upload_log(clean=True)
        loop.close()
