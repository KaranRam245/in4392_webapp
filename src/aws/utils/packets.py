import time as timepackage
import psutil


class HeartBeatPacket(dict):

    def __init__(self, state, time=None, cpu_usage=None, mem_usage=None):
        self.state = state
        self.time = time if time else timepackage.time()
        self.cpu_usage = cpu_usage if cpu_usage else self.get_cpu_usage()
        self.mem_usage = mem_usage if mem_usage else self.get_mem_usage()
        super().__init__(time=self.time, state=str(self.state), cpu_usage=self.cpu_usage,
                         mem_usage=self.mem_usage)

    @staticmethod
    def get_cpu_usage():
        return psutil.cpu_percent()

    @staticmethod
    def get_mem_usage():
        return psutil.virtual_memory().percent
