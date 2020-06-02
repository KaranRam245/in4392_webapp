import json
import socket, socketserver


HOST = '0.0.0.0'
PORT = 8080
ENCODING = 'UTF-8'


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

            received = self.sock.recv(1024)
            print(received.decode(ENCODING))
        except Exception as e:
            print(e)

    def close(self):
        self.sock.close()


if __name__ == '__main__':
    Server.connect('localhost')
