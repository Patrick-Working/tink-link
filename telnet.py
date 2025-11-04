try:
    import uasyncio as asyncio
except:
    import asyncio
import time

class TelnetClient:

    def __init__(self, hostname: str, port: int = 23, username: str = "", password: str = "", init_string: str = ""):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.init_string = init_string
        self.encoding = 'utf-8'
        self.reader = None
        self.writer = None
        self.connected = False
        self.banner_lines = 3

        self.telnetClient = None

        # just for now
        self.reconnect_delay = 1

    async def connect(self):
        print(f"Trying to connect to telnet: {self.hostname}:{self.port}")
        self.reader, self.writer = await asyncio.open_connection(self.hostname, self.port)

        # Read banner, Extron's end with \r\n, and has 3 lines of data
        # Is there way to bypass all of the banners?

        counter = 0
        while counter < self.banner_lines:
            line = await self.reader.readline()

            decoded = line.decode(self.encoding).strip().lower()
            # If we get a password prompt, send it
            if any(prompt in decoded for prompt in ['login:', 'username:', 'user:']):
                await self.send(self.username)

            if decoded == "password:":
                await self.send(self.password)

            counter += 1

        self.connected = True


        # If initialization string is set, send it.
        if self.init_string:
            await asyncio.sleep_ms(50)
            #await asyncio.sleep(1)
            await self.send(self.init_string)

    '''
    async def _auto_login(self, timeout=10):
        """Attempt to automatically log in using readline()."""

        await self.reader.readuntil(b'login: ')
        self.writer.write(self.username + "\r\n")

        await self.reader.readuntil(b'Password:')
        self.writer.write(self.password + "\r\n")



        start_time = time.ticks_ms()
        timeout_ms = timeout * 1000

        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            try:
                line = await self.reader.read(200)
            except asyncio.TimeoutError:
                continue

            if not line:
                break

            decoded = line.decode(self.encoding).strip().lower()

            if any(prompt in decoded for prompt in ['login:', 'username:', 'user:']):
                if self.username != "":
                    await asyncio.sleep_ms(50)
                    await self.send(self.username + '\r\n')
            elif 'password:' in decoded:
                if self.password != "":
                    await asyncio.sleep_ms(50)
                    await self.send(self.password + '\r\n')
                    return  # Done with login
            else:
                return
        print("Login sequence timed out or incomplete.")
    '''
    async def readline(self) -> str:
        while True:
            if not self.connected:
                await self._reconnect()

            try:
                line = await self.reader.readline()
                if not line:
                    self.connected = False
                    continue
                return line.decode(self.encoding).strip()
            except Exception as e:
                self.connected = False
                await asyncio.sleep(self.reconnect_delay)

    async def _reconnect(self):
        print("Reconnecting")
        await self.close()
        await asyncio.sleep(self.reconnect_delay)
        await self.connect()
    
    async def send(self, message: str):
        if self.connected and self.writer:
            message = message + '\r'
            if self.connected and self.writer:
                data = bytes(message, self.encoding)
                self.writer.write(data)
                await self.writer.drain()

    async def close(self):
        if self.writer:
            await self.writer.drain()
            self.writer.close()
            await self.writer.wait_closed()