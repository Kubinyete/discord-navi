import navibot
from navibot import NaviImageViewer
from modules.yandere import YandereApi

async def callbackCreateYandereApiInstance(bot):
    await YandereApi.get_instance(bot).load_tag_summary()

async def command_ynd(bot, message, args, flags, handler):
    if len(args) < 2 or (args[1] == "tag" and len(args) < 3):
        await bot.feedback(message, navibot.COMMAND_INFO, text=handler.usage)
        return

    api = YandereApi.get_instance()

    if "tag" == args[1]:
        tags = api.search_for_tag(" ".join(args[2:]), limit=bot.config.get("external.yandere.max_allowed_tag_output"))

        texttags = f"**{len(tags)} ou mais tags resultantes**\n\n" if len(tags) >= bot.config.get("external.yandere.max_allowed_tag_output") else f"**{len(tags)} tags resultantes**\n\n"

        for tag in tags:
            texttags += f"`{tag}`\n"

        await bot.feedback(message, navibot.SUCCESS, text=texttags)
        return
    elif "post" == args[1]:
        curpage = 1
        try:
            curpage = int(flags["page"])
        except (KeyError, ValueError):
            pass

        naviimages = await api.search_for_post_naviimage(" ".join(args[2:] if len(args) > 2 else ""), limit=bot.config.get("external.yandere.max_allowed_posts_per_page"), page=curpage)

        iv = NaviImageViewer(naviimages, message, title=f'Resultados para: {", ".join(args[2:])}')
        await iv.send_and_wait(bot)
        return
    else:
        await bot.feedback(message, navibot.COMMAND_INFO, text=handler.usage)

LISTEN = {
    "on_ready": [callbackCreateYandereApiInstance]
}