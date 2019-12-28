import discord
import asyncio
import navibot
from navibot import EmbedSlide
from navibot import EmbedSlideItem
from modules.osu import OsuApi

async def command_osu(bot, message, args, flags, handler):
	if len(args) < 3:
		await bot.feedback(message, navibot.COMMAND_INFO, text=handler.usage)
		return

	api = OsuApi.get_instance(bot)

	modeid = 0
	modestrv2 = "osu"

	if "mode" in flags:
		if flags["mode"] == "taiko":
			modeid = 1
			modestrv2 = "taiko"
		elif flags["mode"] == "ctb":
			modeid = 2
			modestrv2 = "fruits"
		elif flags["mode"] == "mania":
			modeid = 3
			modestrv2 = "mania"

	if "profile" == args[1]:
		user = await api.get_user(" ".join(args[2:]), modeid=modeid)

		if len(user) > 0:
			user = user[0]

			domain = bot.config.get("external.osu.api_domain")
			assets = bot.config.get("external.osu.api_assets")
			naviresources = bot.config.get("external.navi.github_resources_url")

			items = [EmbedSlideItem(
				title=f"{user['username']}",
				description=f"""
**#{user['pp_rank']}** (:flag_{user['country'].lower()}: **#{user['pp_country_rank']}**)
**Join date:** {user['join_date']}
**Playtime:** {int(user['total_seconds_played']) / 86400.0 if user['total_seconds_played'] is not None else 0:.2f} day(s)
**Playcount:** {user['playcount']}
**PP:** {user['pp_raw']}
**Accuracy:** {float(user['accuracy']) if user['accuracy'] is not None else 0:.2f}
**Level:** {float(user['level']) if user['level'] is not None else 0:.2f}

*Ver em* [osu.ppy.sh](https://{domain}/u/{user['user_id']})
""",
				url=f"https://{domain}/u/{user['user_id']}",
				thumbnail=f"https://{assets}/{user['user_id']}",
				author=f"Mova o slide para ver as melhores pontuações de {user['username']}"
			)]

			bot.log.write(f"https://{assets}/{user['user_id']}")

			user_best = await api.get_user_best_v2(user['user_id'], modestr=modestrv2, limit=bot.config.get("external.osu.max_allowed_best_scores_per_user"))

			for score in user_best:
				beatmap = score['beatmap']
				beatmapset = score['beatmapset']

				items.append(EmbedSlideItem(
					title=f"{beatmapset['title']} por {beatmapset['artist']} [{beatmap['version']}]",
					url=beatmap['url'],
					image=beatmapset['covers']['card'],
					thumbnail=f"{naviresources}/osu/rank_{score['rank']}.png",
					fields=[
						("Mods", ", ".join(score['mods']), True),
						("Accuracy", f"{score['accuracy'] * 100:.2f}", True),
						("Combo", f"{score['max_combo']}x", True),
						("PP", f"{score['pp']:.2f}pp ({score['weight']['pp']:.2f}pp {score['weight']['percentage']:.2f}%)", True),
						("Stars", f":star: {beatmap['difficulty_rating']}", True)
					]
				))

			await EmbedSlide(items, message).send_and_wait(bot)
		else:
			await bot.feedback(message, navibot.WARNING, text="Não foi encontrado nenhum usuário com o nome informado")
			return

	elif "beatmap" == args[1]:
		pass
	else:
		await bot.feedback(message, navibot.COMMAND_INFO, text=handler.usage)