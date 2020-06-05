import asyncio

from aws.utils.connection import decode_packet, encode_packet


class EchoServer:

    def __init__(self):
        self.received_messages = []

    async def handle_echo(self, reader, writer):
        addr = writer.get_extra_info('peername')

        while True:
            data = await reader.read(1024)
            if data == b"":  # EOF passed.
                break
            packet = decode_packet(data)
            self.received_messages.append(packet)
            print("Received {} from {}".format(packet, addr))

            send_message = encode_packet(packet)
            writer.write(send_message)
            print("Sent: {}".format(packet))
            await writer.drain()
            await asyncio.sleep(2)

        print("Close the client socket of {}".format(addr))
        writer.close()


class ServerWorker:

    def __init__(self, server):
        self.server = server

    async def node_scheduling(self):
        while True:
            print('Doing some work. You have received {} packets so far.'.format(
                len(self.server.received_messages)))

            await asyncio.sleep(10)


def main():
    loop = asyncio.get_event_loop()
    echoserver = EchoServer()
    coro = asyncio.start_server(echoserver.handle_echo, '0.0.0.0', 8080, loop=loop)

    server_worker = ServerWorker(echoserver)
    procs = asyncio.wait([coro, server_worker.node_scheduling()])

    server = loop.run_until_complete(procs)

    # Serve requests until Ctrl+C is pressed
    server_socket = None
    for task in server[0]:
        if task._result:
            server_socket = task._result.sockets[0]
    if server_socket:
        print('Serving on {}'.format(server_socket.getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()


if __name__ == "__main__":
    main()
