import time as timepackage
import psutil


class Packet(dict):

    def __init__(self, packet_type, time, **kwargs):
        time = time if time else timepackage.time()
        super().__init__(packet_type=packet_type, **kwargs)


class HeartBeatPacket(Packet):

    def __init__(self, state, time=None, cpu_usage=None, mem_usage=None):
        cpu_usage = cpu_usage if cpu_usage else self.get_cpu_usage()
        mem_usage = mem_usage if mem_usage else self.get_mem_usage()
        super().__init__(packet_type='HeartBeat',
                         time=time,
                         state=state,
                         cpu_usage=cpu_usage,
                         mem_usage=mem_usage)

    @staticmethod
    def get_cpu_usage():
        return psutil.cpu_percent()

    @staticmethod
    def get_mem_usage():
        return psutil.virtual_memory().percent


class CommandPacket(Packet):

    def __init__(self, command, time=None):
        super().__init__(packet_type='Command', time=time, command=command)


class PacketTranslator:

    @staticmethod
    def translate(packet: dict) -> Packet:
        if packet['packet_type'] == 'HeartBeat':
            return HeartBeatPacket(**packet)
        elif packet['packet_type'] == 'Command':
            return CommandPacket(**packet)
        else:
            raise Exception('Unknown packet provided: {}'.format(packet['packet_type']))
