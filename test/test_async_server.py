import asyncio


class EchoServer:

    def __init__(self):
        self.keep_running = True
        self.received_messages = []

    async def handle_echo(self, reader, writer):
        counter = 0
        while self.keep_running:
            data = await reader.read(100)
            message = data.decode()
            addr = writer.get_extra_info('peername')
            print("Received %r from %r" % (message, addr))

            print("Send: %r" % message)
            writer.write(data)
            await writer.drain()

        print("Close the client socket")
        writer.close()
        reader.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    echoserver = EchoServer()
    coro = asyncio.start_server(echoserver.handle_echo, '0.0.0.0', 8080, loop=loop)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
