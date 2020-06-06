"""
Module for connections.
"""
import json
import asyncio
from abc import abstractmethod
from typing import List

from aws.utils.packets import HeartBeatPacket, PacketTranslator, CommandPacket, Packet

HOST = '0.0.0.0'
PORT = 8080
ENCODING = 'UTF-8'


def encode_packet(data):
    """
    Encode packet, either a string or packet, to bytes.
    :param data: Data in terms of a string or packet.
    :return: Encoded message with the default encoding.
    """
    if isinstance(data, str):
        return data.encode(ENCODING)
    if isinstance(data, Packet):
        return json.dumps(data).encode(ENCODING)
    raise TypeError("Unknown type found for encoding: {}".format(type(data)))


def decode_packet(data) -> Packet:
    """
    Decode bytes into a packet.

    :param data: Bytes received that should represent a packet.
    :return: Decoded packet.
    """
    value = data.decode(ENCODING)
    packet_dict = json.loads(value)
    return PacketTranslator.translate(packet_dict)


class MultiConnectionServer:
    """
    Class for multiple connections handling.
    The code is based on https://github.com/realpython/materials/blob/master/python-sockets-tutorial
    """

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def process_packet(self, message, source) -> Packet:
        """
        Process packet received and return a response packet to send to the client.
        :param message: Message received from the client.
        :param source: Client address.
        :return: Packet to repond to the client.
        """
        packet = PacketTranslator.translate(message)
        if isinstance(packet, CommandPacket):
            raise NotImplementedError()  # The server currently does not take commands.
        if isinstance(packet, HeartBeatPacket):
            return self.process_heartbeat(packet, source)
        raise TypeError("Unknown packet found: {}".format(packet['packet_type']))

    @abstractmethod
    def process_heartbeat(self, hb, source) -> Packet:
        raise NotImplementedError("Server process_heartbeat not implemented yet.")

    async def run(self, reader, writer):
        addr = writer.get_extra_info('peername')

        try:
            while True:
                data = await reader.read(1024)
                if data == b"":  # EOF passed.
                    break
                packet_received = decode_packet(data)
                packet_reponse = self.process_packet(packet_received, addr)
                print("Received {} from {}".format(packet_received, addr))

                print("Sent: {}".format(packet_reponse))
                data_response = encode_packet(packet_reponse)
                writer.write(data_response)
                await writer.drain()
                await asyncio.sleep(2)
        except ConnectionResetError:
            print("Client {} forcibly closed its connection.".format(addr))
        except TypeError as excep:
            print(excep)
        finally:
            print("Closed connection of client: {}".format(addr))
            writer.close()


class MultiConnectionClient:

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.send_buffer: List[Packet] = []
        self.received_packets: List[Packet] = []
        self.running = True

    def send_message(self, message: Packet):
        self.send_buffer.append(message)
        print("Message added to buffer: {}".format(message))

    def process_message(self, message):
        packet = PacketTranslator.translate(message)
        if isinstance(packet, CommandPacket):
            self.process_command(packet['command'])
        elif isinstance(packet, HeartBeatPacket):
            print("Acknowledge on my heartbeat. No additional action to take.")
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
                while self.send_buffer:
                    packet_send: Packet = self.send_buffer.pop(0)

                    print('Sent: {}'.format(packet_send))
                    writer.write(encode_packet(packet_send))

                    data_received = await reader.read(1024)
                    packet_received = decode_packet(data_received)
                    print('Received: {}'.format(packet_received))
                    self.received_packets.append(packet_received)
                    # TODO: process the received messages.

                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            print('Close the socket')
            writer.close()

    def close(self):
        self.running = False
