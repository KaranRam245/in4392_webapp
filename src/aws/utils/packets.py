from time import time


class HeartBeatPacket:

    def __init__(self, state, cpu_usage, mem_usage):
        self.time = time
        self._state = state
        self._cpu_usage = cpu_usage
        self._mem_usage = mem_usage
        super().__init__()
