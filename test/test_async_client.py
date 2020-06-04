import asyncio


class EchoClient:
    def __init__(self):
        self.keep_running = True
        self.received_messages = []

    async def tcp_echo_client(self):
        reader, writer = await asyncio.open_connection('18.157.155.126', 8080)
        counter = 0
        while self.keep_running:
            await asyncio.sleep(1)
            message = 'Hello world ' + str(counter)
            counter += 1
            print('Send: %r' % message)
            writer.write(message.encode())

            data = await reader.read(100)
            print('Received: %r' % data.decode())
            self.received_messages.append(data)

        print('Close the socket')
        writer.close()

    async def keep_doing_stuff(self):
        counter = 0
        while self.keep_running:
            await asyncio.sleep(1.8)
            message = self.received_messages.pop(0)
            print(message.upper())
            counter += 1
            if counter == 10:
                self.close_client()
        print("I've received enough")

    def close_client(self):
        self.keep_running = False


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    echoclient = EchoClient()
    procs = asyncio.wait([echoclient.tcp_echo_client(), echoclient.keep_doing_stuff()])
    loop.run_until_complete(procs)
    loop.close()
