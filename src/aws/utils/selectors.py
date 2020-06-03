

EVENT_READ = 1
EVENT_WRITE = 0


class DefaultSelector:

    def register(self, conn, events, data):
        pass

    def unregister(self, sock):
        pass

    def select(self, timeout):
        return []

    def close(self):
        pass

    def modify(self, fileobj, events, data):
        pass