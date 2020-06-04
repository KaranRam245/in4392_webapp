import asyncio
import boto3

class EchoServer:

    def __init__(self):
        self.received_messages = []

    async def handle_echo(self, reader, writer):
        addr = writer.get_extra_info('peername')

        while True:
            data = await reader.read(1024)
            if data == b"":  # EOF passed.
                break
            message = data.decode()
            self.received_messages.append(message)
            print("Received {} from {}".format(message, addr))

            print("Send: {}".format(message))
            writer.write(data)
            await writer.drain()
            await asyncio.sleep(2)

        print("Close the client socket of {}".format(addr))
        writer.close()

    async def node_scheduling(self):
        sess = boto3.session.Session()
        ec2 = sess.client('ec2')

        while True:
            print(ec2.describe_instances())

            await asyncio.sleep(10)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    echoserver = EchoServer()
    coro = asyncio.start_server(echoserver.handle_echo, '0.0.0.0', 8080, loop=loop)

    procs = asyncio.wait([coro, echoserver.node_scheduling()])

    server = loop.run_until_complete(procs)

    # Serve requests until Ctrl+C is pressed
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
