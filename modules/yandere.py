import asyncio
import aiohttp
import re
import navilog
from navibot import NaviImage

class TagSummary:
    def __init__(self, tagtype, relatives):
        self.type = tagtype
        self.relatives = relatives

class YandereApi:
    unique_instance = None

    def __init__(self, bot):
        self._tags = []
        self._bot = bot

    async def load_tag_summary(self):

        domain = self._bot.config.get("external.yandere.api_domain")
        endpoint = self._bot.config.get("external.yandere.api_gettagsummary")

        self._bot.log.write(f"YandereApi: Carregando sumário de tags através do endpoint: {domain}{endpoint}", logtype=navilog.DEBUG)
        json = await self._bot.http.fetch_json(f"https://{domain}{endpoint}")

        try:
            taggroups = json["data"].split(" ")
            del taggroups[-1]

            for taggroup in taggroups:
                tagdata = taggroup.split("`")

                del tagdata[-1]

                self._tags.append(TagSummary(int(tagdata[0]), tagdata[1:]))
        except KeyError as e:
            self._bot.handle_exception(e)
            return

        self._bot.log.write(f"YandereApi: As tags foram carregadas", logtype=navilog.DEBUG)

    @staticmethod
    def get_instance(bot=None):
        if YandereApi.unique_instance is None and not bot is None:
            YandereApi.unique_instance = YandereApi(bot)
        
        return YandereApi.unique_instance

    def search_for_tag(self, search, limit=0):
        result = []

        for taggroup in self._tags:
            for tag in taggroup.relatives:
                if re.search(search, tag):
                    result.append(tag)

                    if limit > 0 and len(result) >= limit:
                        return result

        return result

    async def search_for_post_naviimage(self, tags, page=1, limit=0):
        domain = self._bot.config.get("external.yandere.api_domain")
        endpoint = self._bot.config.get("external.yandere.api_getpost")
        disablensfw = self._bot.config.get("external.yandere.disable_nsfw")

        imgs = []
        posts = await self._bot.http.fetch_json(f"https://{domain}{endpoint}", params={"tags": tags, "limit": limit, "page": page})

        try:
            for post in posts:
                if not disablensfw or post["rating"] == "s":
                    imgs.append(NaviImage(post["preview_url"], source=post["file_url"]))
        except Exception as e:
            self._bot.handle_exception(e)

        return imgs
