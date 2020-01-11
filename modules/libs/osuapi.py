import asyncio
import navilog
import naviuteis

class OsuApi:
    unique_instance = None

    def __init__(self, bot):
        self._bot = bot

    @staticmethod
    def get_instance(bot=None):
        if OsuApi.unique_instance is None and not bot is None:
            OsuApi.unique_instance = OsuApi(bot)
        
        return OsuApi.unique_instance

    async def get_user(self, username, modeid=0):
        key = self._bot.config.get(f"external.osu.api_key")
        
        return await self._bot.http.fetch_json(f"https://osu.ppy.sh/api/get_user", params={
            "k": key, 
            "u": username, 
            "m": modeid, 
            "type": "string"
        })

    async def get_user_best(self, username, modeid=0, limit=10):
        key = self._bot.config.get(f"external.osu.api_key")
        
        return await self._bot.http.fetch_json(f"https://osu.ppy.sh/api/get_user_best", params={
            "k": key, 
            "u": username, 
            "m": modeid, 
            "limit": limit,
            "type": "string"
        })

    async def get_user_best_v2(self, userid, modestr="osu", limit=10):        
        return await self._bot.http.fetch_json(f"https://osu.ppy.sh/users/{userid}/scores/best", params={
            "mode": modestr, 
            "limit": limit
        })