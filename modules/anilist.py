import discord
import navibot
from navibot import EmbedItem
from navibot import EmbedSlide
from modules.libs.anilistapi import AniListApi

async def callbackCreateAniListApiInstance(bot):
	AniListApi.get_instance(bot)

async def command_anilist(bot, message, args, flags, handler):
	if len(args) < 2:
		await bot.feedback(message, navibot.COMMAND_INFO, usage=handler)
		return

	if args[1] == "character":
		api = AniListApi.get_instance()
		characters = await api.search_characters(" ".join(args[2:]) if len(args) > 2 else "")

		if len(characters) > 0:
			items = [
				EmbedItem(
					title=f"{c.name_full}" if not c.name_native else f"{c.name_full} ({c.name_native})",
					description=c.get_description(),
					thumbnail=c.image_large,
					fields=[
						("Favourites", f":heart: {c.favourites}")
					]
				) for c in characters
			]

			await EmbedSlide(items, message).send_and_wait(bot)
		else:
			await bot.feedback(message, navibot.WARNING, text=f"Nenhum personagem foi encontrado.")
	else:
		await bot.feedback(message, navibot.COMMAND_INFO, usage=handler)

LISTEN = {
	"on_ready": [callbackCreateAniListApiInstance]
}