from threading import Timer


class RepeatingHeartBeat(Timer):

    DEFAULT_INTERVAL = 30

    def __init__(self, *, func, interval=DEFAULT_INTERVAL):
        """
        Create a repeating heartbeat threat with a specified interval.
        :param interval:
        :param func:
        """
        super().__init__(interval, func)

    def run(self):
        """
        Run the Repeating Heartbeat timer.
        """
        try:
            while not self.finished.is_set():
                self.function(*self.args, **self.kwargs)
                self.finished.wait(self.interval)
        except KeyboardInterrupt:
            pass
