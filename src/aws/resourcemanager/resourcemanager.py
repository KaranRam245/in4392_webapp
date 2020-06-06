"""
Module for the Resource Manager.
"""
from aws.utils.monitor import Listener, Observable
import aws.utils.connection as con
from aws.utils.packets import CommandPacket, Packet, HeartBeatPacket, PacketTranslator
from aws.utils.state import InstanceState


class ResourceManagerCore(Observable, con.MultiConnectionServer):

    def __init__(self):
        self._instance_state = InstanceState(InstanceState.RUNNING)

    def process_packet(self, message, source) -> Packet:
        """
        Process packet received and return a response packet to send to the client.
        :param message: Message received from the client.
        :param source: Client address.
        :return: Packet to repond to the client.
        """
        packet = PacketTranslator.translate(message)
        if isinstance(packet, CommandPacket):
            return self.process_command(command=packet, source=source)
        if isinstance(packet, HeartBeatPacket):
            return self.process_heartbeat(packet, source)
        raise TypeError("Unknown packet found: {}".format(packet['packet_type']))

    def generate_heartbeat(self, notify=True) -> HeartBeatPacket:
        """
        Send a heartbeat to the ResourceMonitor.
        """
        hb = HeartBeatPacket(instance_state=self._instance_state,
                             instance_type='resource_manager')
        if notify:
            self.notify(message=hb)
        return hb

    def process_command(self, command: CommandPacket, source) -> Packet:

        return self.generate_heartbeat(notify=False)

    def process_heartbeat(self, hb, source) -> Packet:
        """
        The resource manager should not receive any heartbeats. No action is taken on them.
        The very same heartbeat is simply returned.
        :param hb: Heartbeat message
        :param source: Source address of the heartbeat.
        :return: The same heartbeat as the incoming heartbeat, as no action should be taken.
        """
        return hb


class ResourceMonitor(Listener):

    def __init__(self, monitor_client, monitor_server):
        self.client = monitor_client
        self.server = monitor_server

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format.
        """
        raise NotImplementedError("The class is a listener but has not implemented the event "
                                  "method.")


class ResourceClientWrapper(con.MultiConnectionClient):

    def process_command(self, command: CommandPacket):
        pass


def start_instance(host, port=con.PORT):
    """
    Function to start the Resource manager, which is used to control saving and downloading files.
    :param host: Host address to connect to with the client.
    :param port: Port for the communication channel.
    """
    rm_core = ResourceManagerCore()
    monitor_client = ResourceClientWrapper(host, port)
    monitor_server = ResourceServerWrapper(host, port)
    r_monitor = ResourceMonitor(monitor_client, monitor_server)
    rm_core.add_listener(r_monitor)

    loop = asyncio.get_event_loop()
    server_core = asyncio.start_server(monitor_server.run, host, port, loop=loop)

    procs = asyncio.wait([server_core, monitor_client.run(), rm_core.run()])
