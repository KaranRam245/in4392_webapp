import time as timepackage

import psutil


class Packet(dict):

    def __init__(self, packet_type, time, **kwargs):
        time = time if time else timepackage.time()
        for key, value in kwargs.items():  # Convert all non built-ins to strings.
            if value.__class__.__module__ != 'builtins':
                kwargs[key] = str(value)
        super().__init__(packet_type=packet_type, time=time, **kwargs)


class HeartBeatPacket(Packet):

    def __init__(self, instance_id, instance_state, instance_type, packet_type='HeartBeat',
                 time=None, cpu_usage=None, mem_usage=None, **kwargs):
        cpu_usage = cpu_usage if cpu_usage else self.get_cpu_usage()
        mem_usage = mem_usage if mem_usage else self.get_mem_usage()
        super().__init__(packet_type=packet_type,
                         instance_id=instance_id,
                         time=time,
                         instance_state=instance_state,
                         instance_type=instance_type,
                         cpu_usage=cpu_usage,
                         mem_usage=mem_usage,
                         **kwargs)

    @staticmethod
    def get_cpu_usage():
        return psutil.cpu_percent()

    @staticmethod
    def get_mem_usage():
        return psutil.virtual_memory().percent


class CommandPacket(Packet):

    def __init__(self, command, packet_type='Command', args: dict = None, time=None, **kwargs):
        if args is None:
            args = {}
        super().__init__(packet_type=packet_type, time=time, command=command, args=args, **kwargs)


class MetricPacket(Packet):

    def __init__(self, download_duration: float, upload_duration: float, packet_type='Metric', time=None, **kwargs):
        super().__init__(packet_type=packet_type, time=time, download_duration=download_duration, upload_duration=upload_duration)

class PacketTranslator:

    @staticmethod
    def translate(packet: dict) -> Packet:
        if packet['packet_type'] == 'HeartBeat':
            return HeartBeatPacket(**packet)
        if packet['packet_type'] == 'Command':
            return CommandPacket(**packet)
        if packet['packet_type'] == 'Metric':
            return MetricPacket(**packet)
        raise Exception('Unknown packet provided: {}'.format(packet['packet_type']))

