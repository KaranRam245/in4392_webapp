import socket, socketserver
from abc import ABC, abstractmethod
from _thread import *


HOST = 'localhost'
PORT = 8080


class Server(socketserver.BaseRequestHandler):

    def handle(self):
        data = self.request.recv(1024).strip()
        data = data.decode('UTF-8')
        print("{} wrote:\n{}".format(self.client_address[0], data))
        self.request.sendall(data.upper().encode('UTF-8'))

    @staticmethod
    def connect():
        try:
            server = socketserver.TCPServer((HOST, PORT), Server)
            print('Monitor is running')
            server.serve_forever()
        except Exception as e:
            print(e)

class Client:
    def __init__(self, host=HOST, port=PORT):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = HOST
        self.port = PORT
        self._connect()

    def _connect(self):
        try:
            self.sock.connect((self.host, self.port))
        except Exception as e:
            print(e)

    def send(self, message):
        try:
            self.sock.sendall(message.encode('UTF-8'))

            received = self.sock.recv(1024)
            print(received.decode('UTF-8'))
        except Exception as e:
            print(e)

    def close(self):
        self.sock.close()


class SomeMonitor(Server):

    def __init__(self):
        self.connect()


def start_monitor():
    monitor = SomeMonitor()
