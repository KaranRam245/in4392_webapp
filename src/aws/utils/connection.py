import json
import asyncio
from abc import abstractmethod

from aws.utils.packets import HeartBeatPacket, PacketTranslator, CommandPacket, Packet

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

    def process_packet(self, message, source) -> Packet:
        if isinstance(message, str):
            message = json.dumps(message)
        packet = PacketTranslator.translate(message)
        if isinstance(packet, CommandPacket):
            raise NotImplementedError()  # The server currently does not take commands.
        if isinstance(packet, HeartBeatPacket):
            return self.process_heartbeat(packet, source)
        print("Unknown packet found: {}".format(packet['packet_type']))

    @abstractmethod
    def process_heartbeat(self, hb, source) -> Packet:
        raise NotImplementedError("Server process_heartbeat not implemented yet.")

    async def run(self, reader, writer):
        addr = writer.get_extra_info('peername')

        while True:
            data = await reader.read(1024)
            if data == b"":  # EOF passed.
                break
            message = data.decode(ENCODING)
            packet_reponse = self.process_packet(message, addr)
            print("Received {} from {}".format(message, addr))

            writer.write(packet_reponse)
            print("Sent: {}".format(packet_reponse))
            await writer.drain()
            await asyncio.sleep(2)

        print("Closed connection of client: {}".format(addr))
        writer.close()


class MultiConnectionClient:

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.send_buffer = []
        self.received_messages = []
        self.running = True

    def send_message(self, message):
        self.send_buffer.append(message)
        print("Message added to buffer: {}".format(message))

    def process_message(self, message):
        packet = PacketTranslator.translate(message)
        if isinstance(packet, CommandPacket):
            self.process_command(packet['command'])
        elif isinstance(packet, HeartBeatPacket):
            print("Someone send me a heartbeat. This should not happen.")
        else:
            print("I do not know this packet type: {}".format(packet['packet_type']))

    @abstractmethod
    def process_command(self, command: CommandPacket):
        raise NotImplementedError("Client has not yet implemented process_command.")

    async def run(self):
        print('Attempting to connect to {}:{}'.format(self.host, self.port))
        reader, writer = await asyncio.open_connection(self.host, self.port)

        try:
            while self.running:
                await asyncio.sleep(1)

                while self.send_buffer:
                    message = self.send_buffer.pop(0)

                    print('Sent: {}'.format(message))
                    writer.write(message.encode(ENCODING))

                    data = await reader.read(1024)
                    print('Received: {}'.format(data.decode()))
                    self.received_messages.append(data)
                    # TODO: process the received messages.

                await asyncio.sleep(5)  # Wait 5 seconds before sending another heartbeat.
        except KeyboardInterrupt:
            pass
        finally:
            print('Close the socket')
            writer.close()

    def close(self):
        self.running = False
