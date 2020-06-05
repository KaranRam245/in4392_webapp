"""
Module for the Node Worker.
"""
from aws.utils.monitor import Observable, Listener
from aws.utils.packets import CommandPacket


class WorkerCore(Observable):
    """
    The WorkerCore accepts the task from the Node Manager.
    """

    def run(self):
        """
        Start function for the WorkerCore.
        """
        raise NotImplementedError()


class WorkerMonitor(Listener):

    def __init__(self):
        pass

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format.
        """
        raise NotImplementedError("The class is a listener but has not implemented the event "
                                  "method.")

    def process_command(self, command: CommandPacket):
        if command['command'] == 'stop':
            self.running = False
        elif command['command'] == 'task':
            raise NotImplementedError("Client has not yet implemented process_command.")
        else:
            print('Received unknown command: {}'.format(command['command']))
