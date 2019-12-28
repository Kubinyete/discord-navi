import discord
import navibot

async def command_osu(bot, message, args, flags, handler):
	if len(args) < 2:
		await bot.feedback(message, navibot.COMMAND_INFO, text=handler.usage)
		return

	modeid = 0

	if "mode" in flags:
		if flags["mode"] == "taiko":
			modeid = 1
		elif flags["mode"] == "ctb":
			modeid = 2
		elif flags["mode"] == "mania":
			modeid = 3

	try:
		json = await bot.http.fetch_json("https://{}{}".format(bot.config.get("external.osu.api_domain"), bot.config.get("external.osu.api_getuser")), {"k": bot.config.get("external.osu.api_key"), "u": " ".join(args[1:]), "m": modeid, "type": "string"})

		if len(json) > 0:
			json = json[0]
		else:
			await bot.feedback(message, navibot.WARNING, text="Não foi encontrado nenhum usuário com esse nome")
			return
	except Exception as e:
		await bot.feedback(message, navibot.ERROR, exception=e)
		return

	description = """
**#{rank}** (:flag_{country}: **#{countryrank}**)
**Join date:** {joindate}
**Playtime:** {playtime:.2f} day(s)
**Playcount:** {playcount}
**PP:** {ppraw}
**Accuracy:** {accuracy:.2f}
**Level:** {level:.2f}
*Ver em* [osu.ppy.sh]({link})
""".format(
		rank=json["pp_rank"], 
		country=json["country"].lower(), 
		countryrank=json["pp_country_rank"], 
		joindate=json["join_date"], 
		playtime=int(json["total_seconds_played"]) / 86400 if json["total_seconds_played"] is not None else 0, 
		playcount=json["playcount"], 
		ppraw=json["pp_raw"], 
		accuracy=float(json["accuracy"]) if json["accuracy"] is not None else 0, 
		level=float(json["level"]) if json["level"] is not None else 0, 
		link="https://" + bot.config.get("external.osu.api_domain") + "/u/" + json["user_id"]
	)

	embed = discord.Embed(title="Perfil de " + json["username"], description=description,color=discord.Colour.magenta())
	embed.set_thumbnail(url="https://" + bot.config.get("external.osu.api_assets") + "/" + json["user_id"])
	embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

	await message.channel.send(embed=embed)
	await bot.feedback(message, navibot.SUCCESS)
