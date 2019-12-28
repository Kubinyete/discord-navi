import aiohttp

class HttpWorker:
    def __init__(self, bot):
        self._session = aiohttp.ClientSession()
        self._bot = bot

    async def close(self):
        """Fecha a sessão HTTP atual.
        """

        await self._session.close()

    async def fetch_json(self, url, params={}):
        """Efetua uma requisição GET, para o url informado, passando juntamente os paramêtros na query.
        
        Args:
            url (str): O URL destino.
            params (dict, optional): Dicionário de parâmetros a ser incluido na requisição.
        
        Returns:
            dict: Objeto dicionário resultando da resposta JSON recebida, caso a conversão falhe, resultará em uma exceção.
        """

        async with self._session.get(url, params=params) as resp:
            return await resp.json()