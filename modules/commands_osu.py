import discord
import asyncio
import navibot
from navibot import EmbedSlide
from navibot import EmbedItem
from modules.osu import OsuApi

async def command_osu(bot, message, args, flags, handler):
	if len(args) < 3:
		await bot.feedback(message, navibot.COMMAND_INFO, usage=handler)
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

			domain = bot.config.get(f"external.{handler.name}.api_domain")
			assets = bot.config.get(f"external.{handler.name}.api_assets")
			naviresources = bot.config.get(f"external.{handler.name}.rank_resources_url")

			items = [EmbedItem(
				title=f"{user['username']}",
				description=f"**#{user['pp_rank']}** (:flag_{user['country'].lower()}: **#{user['pp_country_rank']}**)",
				url=f"https://{domain}/u/{user['user_id']}",
				thumbnail=f"https://{assets}/{user['user_id']}",
				author=f"Mova o slide para ver as melhores pontuações de {user['username']}",
				fields=[
					("Join date", user['join_date'], True),
					("Playtime", f"{int(user['total_seconds_played']) / 86400.0 if user['total_seconds_played'] is not None else 0:.2f} day(s)", True),
					("Playcount", user['playcount'], True),
					("PP", user['pp_raw'], True),
					("Accuracy", f"{float(user['accuracy']) if user['accuracy'] is not None else 0:.2f}", True),
					("Level", f"{float(user['level']) if user['level'] is not None else 0:.2f}", True)
				]
			)]

			user_best = await api.get_user_best_v2(user['user_id'], modestr=modestrv2, limit=bot.config.get(f"external.{handler.name}.max_allowed_best_scores_per_user"))

			for score in user_best:
				beatmap = score['beatmap']
				beatmapset = score['beatmapset']

				items.append(EmbedItem(
					title=f"{beatmapset['title']} por {beatmapset['artist']} [{beatmap['version']}]",
					url=beatmap['url'],
					image=beatmapset['covers']['card'],
					thumbnail=f"{naviresources}/osu/rank_{score['rank']}.png",
					fields=[
						("Mods", ", ".join(score['mods']) if len(score['mods']) > 0 else "Not used", True),
						("Accuracy", f"{score['accuracy'] * 100:.2f}", True),
						("Combo", f"{score['max_combo']}x", True),
						("PP", f"{score['pp']:.2f}pp ({score['weight']['pp']:.2f}pp {score['weight']['percentage']:.2f}%)", True),
						("Stars", f":star: {beatmap['difficulty_rating']}", True)
					]
				))

			await EmbedSlide(items, message).send_and_wait(bot)
		else:
			await bot.feedback(message, navibot.WARNING, text="Não foi encontrado nenhum usuário com o nome informado")
	# elif "beatmap" == args[1]:
	# 	beatmapsets_search = await api.search_beatmapsets_v2("%20".join(args[2:]), modeid=modeid)

	# 	domain = bot.config.get("external.osuv2.api_domain")
		
	# 	cursor = beatmapsets_search['cursor']
	# 	beatmapsets = beatmapsets_search['beatmapsets']
	# 	total = beatmapsets_search['total']

	# 	if total > 0:
	# 		items = []

	# 		for beatmapset in beatmapsets:
	# 			fields = []

	# 			for beatmapdiff in beatmapset['beatmaps']:
	# 				fields.append(
	# 					(
	# 						f"[{beatmapdiff['version']}] ({beatmapdiff['mode']})", 
	# 						f"AR: {beatmapdiff['ar']}, OD: {beatmapdiff['accuracy']}, CS: {beatmapdiff['cs']}, HP: {beatmapdiff['drain']}, Stars: :star: {beatmapdiff['difficulty_rating']}"
	# 					)
	# 				)

	# 			fields.append(("Creator", beatmapset['creator'] if beatmapset['creator'] else "Not available", True))
	# 			fields.append(("BPM", beatmapset['bpm'] if beatmapset['bpm'] else "Not available", True))
	# 			fields.append(("Source", beatmapset['source'] if beatmapset['source'] else "Not available", True))
	# 			fields.append(("Download", f"[Download beatmapset](https://{domain}/beatmapsets/{beatmapset['id']}/download)" if not beatmapset['availability']['download_disabled'] else "This beatmapset is no longer available for download.", True))

	# 			items.append(EmbedItem(
	# 				title=f"{beatmapset['title']} por {beatmapset['artist']}",
	# 				url=f"https://{domain}/beatmapsets/{beatmapset['id']}",
	# 				image=beatmapset['covers']['card'],
	# 				fields=fields
	# 			))

	# 		await EmbedSlide(items, message).send_and_wait(bot)
	# 	else:
	# 		await bot.feedback(message, navibot.WARNING, text="Não foi encontrado nenhum beatmapset")
	else:
		await bot.feedback(message, navibot.COMMAND_INFO, usage=handler)