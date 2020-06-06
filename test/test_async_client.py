import asyncio
import sys

from aws.utils.packets import HeartBeatPacket
from aws.utils.connection import encode_packet, decode_packet


class EchoClient:
    def __init__(self, host, port):
        self.keep_running = True
        self.received_packets = []
        self.host = host
        self.port = port

    async def tcp_echo_client(self):
        print('Attempting to connect to {}:{}'.format(self.host, self.port))
        reader, writer = await asyncio.open_connection(self.host, self.port)
        counter = 0
        while self.keep_running:
            await asyncio.sleep(1)
            send_packet = HeartBeatPacket(1, instance_state=1, instance_type='worker')
            counter += 1
            print('Send: {}'.format(send_packet))
            writer.write(encode_packet(send_packet))

            data = await reader.read(1024)
            if data == b"":  # EOF passed.
                print("Connection forcibly closed by host. EOF received.")
                break
            received_packet = decode_packet(data)
            print('Received: {}'.format(received_packet))
            self.received_packets.append(received_packet)

        print('Close the socket')
        writer.close()

    async def keep_doing_stuff(self):
        counter = 0
        while self.keep_running:
            await asyncio.sleep(1.8)
            if self.received_packets:
                packet = self.received_packets.pop(0)
                print('Doing stuff with: {}'.format(packet))
                counter += 1
                if counter == 10:
                    self.close_client()
        print("I've received enough")

    def close_client(self):
        self.keep_running = False


if __name__ == "__main__":
    args = list(sys.argv)
    if len(args) < 2:
        print(args)
        args.append('127.0.0.1')
    loop = asyncio.get_event_loop()
    echoclient = EchoClient(args[1], 8080)
    procs = asyncio.wait([echoclient.tcp_echo_client(), echoclient.keep_doing_stuff()])
    loop.run_until_complete(procs)
    loop.close()
