import aiohttp

class HttpWorker:
    def __init__(self, bot):
        self._session = aiohttp.ClientSession()
        self._bot = bot

    async def close(self):
        await self._session.close()

    async def fetch_json(self, url, params={}):
        async with self._session.get(url, params=params) as resp:
            return await resp.json()