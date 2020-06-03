import json
# import selectors
import socket
from abc import abstractmethod
from time import sleep
import aws.utils.selectors as selectors

from aws.utils.packets import HeartBeatPacket, PacketTranslator, CommandPacket

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
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(conn, events, data=data)

    def service_connection(self, key, mask):
        try:
            sock = key.fileobj
            data = key.data
            if mask & selectors.EVENT_READ:
                recv_data = sock.recv(1024)
                if recv_data:
                    data['outb'] += recv_data  # TODO: Process.
                    message = json.loads(recv_data.decode(ENCODING))
                    print('Processing: {}'.format(message))
                    self.process_packet(message, data['addr'])
                else:
                    print("Closing connection to", data['addr'])
                    self.sel.unregister(sock)
                    sock.close()
            if mask & selectors.EVENT_WRITE:
                if data['outb']:
                    print("Echoing: {}, to: {}".format(data['outb'], data['addr']))
                    sock.sendall(data['outb'])
                    data['outb'] = b""
        except ConnectionResetError:
            self.sel.unregister(key.fileobj)

    def process_packet(self, message, source):
        packet = PacketTranslator.translate(message)
        if isinstance(packet, CommandPacket):
            pass  # The server currently does not take commands.
        elif isinstance(packet, HeartBeatPacket):
            self.process_heartbeat(packet, source)
        else:
            print("Unknown packet found: {}".format(packet['packet_type']))

    @abstractmethod
    def process_heartbeat(self, hb, source):
        print("Heartbeat: {}, from: {}".format(hb, source))
        # TODO: process heartbeat

    def run(self, lock):
        print('Starting Server instance..')
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.bind((self.host, self.port))
        lsock.listen(10)  # Maximum nodes that can connect. If needed this can be leveraged.
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, data=None)
        print('Listening on {}:{}'.format(self.host, self.port))

        try:
            while True:
                events = self.sel.select(timeout=None)
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
        print("Sending message: {}".format(message))
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
                recv_decoded = recv_data.decode(ENCODING)
                print("Received:", recv_decoded, "from connection:", self.host)
                recv_message = json.loads(recv_data.decode(ENCODING))
                self.process_message(recv_message)
                data['recv_total'] += len(recv_data)
            if not recv_data:
                print("Closing connection")
                self.sel.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE:
            while self.message_buffer:
                message = self.message_buffer[0]
                print("Sending", message, "to connection", self.host)
                self.sock.sendall(json.dumps(message).encode(ENCODING))
                self.message_buffer.pop(0)
                data['messages_sent'] += 1
            self.sel.modify(key.fileobj, events=selectors.EVENT_READ, data=data)

    def process_message(self, message):
        packet = PacketTranslator.translate(message)
        if isinstance(packet, CommandPacket):
            self.process_command(packet['command'])
        elif isinstance(packet, HeartBeatPacket):
            print("Someone send me a heartbeat. This should not happen.")
        else:
            print("I do not know this packet type: {}".format(packet['packet_type']))

    @abstractmethod
    def process_command(self, command):
        raise NotImplementedError("Client has not yet implemented process_command.")

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
            pass
        except OSError:
            print("Server appears to be down. Waiting for a retry.")
            sleep(5)
            self.start_connection()
        finally:
            self.sel.close()

    def run(self):
        try:
            while True:
                print('...')
                self.send_message(HeartBeatPacket(1))
                # self.send_message({'test':'message'})
                self._send_buffer()
                sleep(5)
        except KeyboardInterrupt:
            pass
