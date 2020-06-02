import time as timepackage


class HeartBeatPacket(dict):

    def __init__(self, state, cpu_usage, mem_usage, time=None):
        self.time = time if time else timepackage.time()
        self.state = state
        self.cpu_usage = cpu_usage
        self.mem_usage = mem_usage
        super().__init__(time=self.time, state=str(self.state), cpu_usage=self.cpu_usage,
                         mem_usage=self.mem_usage)
