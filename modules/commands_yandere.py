import navibot
import naviuteis
from navibot import EmbedSlide
from navibot import EmbedSlideItem
from modules.yandere import YandereApi

async def callbackCreateYandereApiInstance(bot):
    await YandereApi.get_instance(bot).load_tag_summary()

async def command_ynd(bot, message, args, flags, handler):
    if len(args) < 2:
        await bot.feedback(message, navibot.COMMAND_INFO, text=handler.usage)
        return

    api = YandereApi.get_instance()

    if "tag" == args[1]:
        tags = api.search_for_tag(" ".join(args[2:]), re="re" in flags)

        if len(tags) > 0:
            items = []
            per_page = bot.config.get("external.yandere.max_allowed_tags_per_page")
            rindex = per_page - 1
            lindex = 0

            while lindex < len(tags):
                current_slice = tags[lindex:rindex]

                items.append(EmbedSlideItem(
                    title="Resultados da busca",
                    description='`' + "\n".join(current_slice) + '`',
                ))

                lindex = rindex + 1
                rindex += per_page

            await EmbedSlide(items, message).send_and_wait(bot)
        else:
            await bot.feedback(message, navibot.WARNING, text=f"Nenhuma tag foi encontrada")


    elif "post" == args[1]:
        
        page = 1
        
        try:
            page = int(flags["page"])
        except (KeyError, ValueError):
            pass

        search = " ".join(args[2:] if len(args) > 2 else "")

        result = await api.search_for_post(search, limit=bot.config.get("external.yandere.max_allowed_posts_per_page"), page=page)
        
        domain = bot.config.get("external.yandere.api_domain")
        postshow = bot.config.get("external.yandere.api_postshow")
        disablensfw = bot.config.get("external.yandere.disable_nsfw")

        if len(result) > 0:
            items = []

            for post in result:
                if not disablensfw or post['rating'] == "s":
                    items.append(EmbedSlideItem(
                        title=f"{post['id']}",
                        url=f"https://{domain}/{postshow}{post['id']}",
                        description=f"""
    `{post['tags']}`
    Ver [amostra]({post['sample_url']}) ({post['sample_width']}x{post['sample_height']}) ({naviuteis.bytes_string(post['sample_file_size'])})
    Ver [original]({post['file_url']}) ({post['width']}x{post['height']}) ({post['file_ext']}, {naviuteis.bytes_string(post['file_size'])})
    """,
                        author=f"Alguns resultados podem estar ocultos devido as configurações de conteúdo." if disablensfw else "",
                        image=f"{post['preview_url']}",
                    ))

            await EmbedSlide(items, message).send_and_wait(bot)
        else:
            await bot.feedback(message, navibot.WARNING, text=f"Nenhuma imagem foi encontrada para o conjunto de tags:\n`{search}`")
    else:
        await bot.feedback(message, navibot.COMMAND_INFO, text=handler.usage)

LISTEN = {
    "on_ready": [callbackCreateYandereApiInstance]
}