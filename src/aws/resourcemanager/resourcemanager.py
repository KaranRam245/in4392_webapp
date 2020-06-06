"""
Module for the Resource Manager.
"""
from aws.utils.monitor import Listener, Observable
import aws.utils.connection as con
from aws.utils.packets import CommandPacket, Packet, HeartBeatPacket, PacketTranslator
from aws.utils.state import InstanceState


class ResourceManagerCore(Observable):

    def __init__(self):
        super().__init__()
        self._instance_state = InstanceState(InstanceState.RUNNING)

    def run(self):
        self.notify("Doing some reading action.")


class ResourceMonitor(Listener):

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format.
        """
        raise NotImplementedError("The class is a listener but has not implemented the event "
                                  "method.")
