import ssl

import certifi
from aiohttp import ClientSession, TCPConnector


class HttpClient:
    session: ClientSession | None = None

    def start(self) -> None:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        conn = TCPConnector(ssl=ssl_context)
        self.session = ClientSession(connector=conn, auto_decompress=True)

    async def stop(self) -> None:
        if self.session is None:
            return

        await self.session.close()
        self.session = None

    def __call__(self) -> ClientSession:
        assert self.session is not None
        return self.session
