import time as timepackage


class HeartBeatPacket(dict):

    def __init__(self, state, cpu_usage, mem_usage, time=None):
        self._time = time if time else timepackage.time()
        self._state = state
        self._cpu_usage = cpu_usage
        self._mem_usage = mem_usage
        super().__init__(time=self._time, state=str(self._state), cpu_usage=self._cpu_usage,
                         mem_usage=self._mem_usage)
