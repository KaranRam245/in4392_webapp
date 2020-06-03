import json
import socket, socketserver
import selectors

from aws.utils.packets import HeartBeatPacket
from time import sleep

HOST = '0.0.0.0'
PORT = 8080
ENCODING = 'UTF-8'


class MultiConnectionServer:
    """
    Class for multiple connections handling.
    The code is based on https://github.com/realpython/materials/blob/master/python-sockets-tutorial
    """

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sel = selectors.DefaultSelector()

    def accept_wrapper(self, sock: socket):
        conn, addr = sock.accept()
        conn.setblocking(False)
        data = {'addr': addr, 'inb': b"", 'outb': b""}
        events = selectors.EVENT_READ
        self.sel.register(conn, events, data=data)

    def service_connection(self, key, mask):
        try:
            sock = key.fileobj
            data = key.data
            if mask & selectors.EVENT_READ:
                recv_data = sock.recv(1024)
                if recv_data:
                    data['outb'] += recv_data  # TODO: Process.
                    print("Received: {}, from: {}".format(json.loads(recv_data.decode(ENCODING)),
                                                          data['addr']))
                else:
                    print("Closing connection to", data['addr'])
                    self.sel.unregister(sock)
                    sock.close()
            if mask & selectors.EVENT_WRITE:
                print("Echoing to ", data['addr'])
                sock.sendall(json.dumps(data['outb']).encode(ENCODING))
        except ConnectionResetError:
            self.sel.unregister(key.fileobj)

    def run(self):
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.bind((self.host, self.port))
        lsock.listen(10)  # Maximum nodes that can connect. If needed this can be leveraged.
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, data=None)

        try:
            while True:
                events = self.sel.select(timeout=None)  # TODO: timeout
                for key, mask in events:
                    if key.data:
                        self.service_connection(key, mask)
                    else:
                        self.accept_wrapper(key.fileobj)
        except KeyboardInterrupt:
            print("Interrupted manually.")
        finally:
            lsock.close()
            self.sel.close()


class MultiConnectionClient:

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sel = selectors.DefaultSelector()
        self.sock = self.start_connection()
        self.message_buffer = []

    def start_connection(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("Initiating connection to {}:{}".format(self.host, self.port))
        sock.setblocking(False)
        sock.connect_ex((self.host, self.port))
        return sock

    def send_message(self, message):
        events = selectors.EVENT_WRITE
        data = {
            'recv_total': 0,
            'messages_sent': 0
        }
        self.message_buffer.append(message)
        try:
            self.sel.register(self.sock, events, data=data)
        except KeyError:
            pass  # Already registered.

    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)
            if recv_data:
                recv_message = json.loads(recv_data.decode(ENCODING))
                print("Received:", recv_message, "from connection:", self.host)
                data['recv_total'] += len(recv_data)
            if not recv_data:
                print("Closing connection")
                self.sel.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE:
            while self.message_buffer:
                message = self.message_buffer.pop(0)
                print("Sending", message, "to connection", self.host)
                self.sock.sendall(json.dumps(message).encode(ENCODING))
                data['messages_sent'] += 1
            self.sel.modify(key.fileobj, events=selectors.EVENT_READ, data=data)

    def close(self):
        self.sel.close()

    def _send_buffer(self):
        try:
            while True:
                events = self.sel.select(timeout=1)
                if events:
                    for key, mask in events:
                        self.service_connection(key, mask)
                    # Check for a socket being monitored to continue.
                else:
                    break
        except KeyboardInterrupt:
            print("Manual program interruption initiated..")
        except OSError:
            print("Server appears to be down. Waiting for a retry.")
            sleep(5)
            self._send_buffer()
        finally:
            self.sel.close()

    def run(self):
        while True:
            print('...')
            self.send_message(HeartBeatPacket(1))
            # self.send_message({'test':'message'})
            self._send_buffer()
            sleep(5)


class Server(socketserver.BaseRequestHandler):

    def handle(self):
        data = self.request.recv(1024).strip()
        data = data.decode('UTF-8')
        print("{} wrote:\n{}".format(self.client_address[0], data))
        self.request.sendall(data.upper().encode(ENCODING))

    @staticmethod
    def connect(host=HOST):
        try:
            server = socketserver.TCPServer((host, PORT), Server)
            print('Monitor is running')
            server.serve_forever()
        except Exception as e:
            print(e)


class Client:
    def __init__(self, host, port=PORT):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host = host
        self.port = port
        self._connect()

    def _connect(self):
        try:
            self.sock.connect((self.host, self.port))
        except Exception as e:
            print(e)

    def send(self, message: dict):
        message = json.dumps(message)
        try:
            self.sock.sendall(message.encode('UTF-8'))
        except Exception as e:
            print(e)

    def close(self):
        self.sock.close()


if __name__ == '__main__':
    Server.connect('localhost')

if __name__ == '__main__':
    MultiConnectionClient().run()

if __name__ == '__main__':
    MultiConnectionServer().run()
