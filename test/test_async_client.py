import asyncio
import sys


class EchoClient:
    def __init__(self, host, port):
        self.keep_running = True
        self.received_messages = []
        self.host = host
        self.port = port

    async def tcp_echo_client(self):
        print('Attempting to connect to {}:{}'.format(self.host, self.port))
        reader, writer = await asyncio.open_connection(self.host, self.port)
        counter = 0
        while self.keep_running:
            await asyncio.sleep(1)
            message = 'Hello world ' + str(counter)
            counter += 1
            print('Send: %r' % message)
            writer.write(message.encode())

            data = await reader.read(100)
            if data == b"":  # EOF passed.
                print("Connection forcibly closed by host. EOF received.")
                break
            print('Received: %r' % data.decode())
            self.received_messages.append(data)

        print('Close the socket')
        writer.close()

    async def keep_doing_stuff(self):
        counter = 0
        while self.keep_running:
            await asyncio.sleep(1.8)
            if self.received_messages:
                message = self.received_messages.pop(0)
                print(message.upper())
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
