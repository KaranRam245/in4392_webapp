"""
Module for connections.
"""
import json
import asyncio
import traceback
from abc import abstractmethod
from typing import List

from aws.utils import config
from aws.utils.packets import HeartBeatPacket, PacketTranslator, CommandPacket, Packet
from aws.resourcemanager.resourcemanager import log_info, log_error, log_exception

HOST = '0.0.0.0'
PORT_IM = 8080
PORT_NM = 8081
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
    try:
        packet_dict = json.loads(value)
        return PacketTranslator.translate(packet_dict)
    except json.JSONDecodeError as e:
        log_error("JsonDecodeError on: {} with {}: {}".format(value, e, traceback.print_exc()))
        raise e

class MultiConnectionServer:
    """
    Class for multiple connections handling.
    The code is based on https://github.com/realpython/materials/blob/master/python-sockets-tutorial
    """

    def __init__(self, host, port):
        self.host = host
        self.port = port
        log_info("Serving on {}:{}..".format(self.host, self.port))

    def process_packet(self, message, source) -> Packet:
        """
        Process packet received and return a response packet to send to the client.
        :param message: Message received from the client.
        :param source: Client address.
        :return: Packet to repond to the client.
        """
        packet = PacketTranslator.translate(message)
        if isinstance(packet, CommandPacket):
            return self.process_command(packet, source)
        if isinstance(packet, HeartBeatPacket):
            return self.process_heartbeat(packet, source)
        raise TypeError("Unknown packet found: {}".format(packet['packet_type']))

    @abstractmethod
    def process_heartbeat(self, heartbeat, source) -> Packet:
        raise NotImplementedError("Server process_heartbeat not implemented yet.")

    @abstractmethod
    def process_command(self, command, source) -> Packet:
        raise NotImplementedError("Server process_command not implemented yet.")

    async def run(self, reader, writer):
        addr = writer.get_extra_info('peername')

        try:
            while True:
                data = await reader.read(1024)
                if data == b"":  # EOF passed.
                    break
                packet_received = decode_packet(data)
                packet_reponse = self.process_packet(packet_received, addr)
                log_info("+ Received: {} from {}".format(packet_received, addr))

                log_info("- Sent: {}".format(packet_reponse))
                data_response = encode_packet(packet_reponse)
                writer.write(data_response)
                await writer.drain()
                await asyncio.sleep(config.SERVER_SLEEP_TIME)
        except ConnectionResetError:
            log_exception("Client {} forcibly closed its connection.".format(addr))
        except TypeError as excep:
            log_exception(str(excep))
        finally:
            log_info("Closed connection of client: {}".format(addr))
            writer.close()


class MultiConnectionClient:

    def __init__(self, host, port, sleep_time=config.CLIENT_SEND_SLEEP):
        self.host = host
        self.port = port
        self.send_buffer: List[Packet] = []
        self.received_packets: List[Packet] = []
        self.running = True
        self._sleep_time = sleep_time

    def send_message(self, message: Packet):
        self.send_buffer.append(message)

    def process_message(self, message):
        packet = PacketTranslator.translate(message)
        if isinstance(packet, CommandPacket):
            self.process_command(packet['command'])
        elif isinstance(packet, HeartBeatPacket):
            log_info("Acknowledge on my heartbeat. No additional action to take.")
            self.process_heartbeat(packet)
        else:
            log_error("I do not know this packet type: {}".format(packet['packet_type']))

    def process_heartbeat(self, hearbeat: HeartBeatPacket):
        log_info("Acknowledge on my heartbeat. No additional action to take.")

    @abstractmethod
    def process_command(self, command: CommandPacket):
        raise NotImplementedError("Client has not yet implemented process_command.")

    async def run(self):
        log_info('Attempting to connect to {}:{}'.format(self.host, self.port))
        reader, writer = await asyncio.open_connection(self.host, self.port)

        try:
            while self.running:
                while self.send_buffer:
                    packet_send: Packet = self.send_buffer.pop(0)

                    log_info('- Sent: {}'.format(packet_send))
                    writer.write(encode_packet(packet_send))

                    data_received = await reader.read(1024)
                    if data_received == b"":  # EOF passed.
                        break
                    packet_received = decode_packet(data_received)
                    log_info('+ Received: {}'.format(packet_received))
                    self.received_packets.append(packet_received)
                    # TODO: process the received messages.

                await asyncio.sleep(self._sleep_time)
        except KeyboardInterrupt:
            pass
        finally:
            log_info('Close the socket')
            writer.close()

    def close(self):
        self.running = False
