import discord
import re
import datetime
import navibot
from navicallbacks import callbackRemind
from naviclient import NaviRoutine
from navibot import NaviImageViewer

# @SECTION
# Comandos disponibilizados por padrão pelo bot

async def command_owner_helloworld(bot, message, args, flags, handler):
    await bot.feedback(message, feedback=navibot.SUCCESS, title="Hello world!", text="Olá mundo!")

async def command_owner_imageviewer(bot, message, args, flags, handler):
	if len(args) < 2:
		await bot.feedback(message, feedback=navibot.ERROR, text="É preciso informar uma lista de URLs como argumentos")
		return
	
	iv = NaviImageViewer(args[1:], message, "imageviewer")
	await iv.send_and_wait(bot)

async def command_help(bot, message, args, flags, handler):
	if len(args) < 2:
		helptext = "**Comandos disponíveis**\n\n"

		for key in bot.commands.get_commands().keys():
			helptext = helptext + "**{}**\n`{}`\n\n".format(key, bot.commands.get(key).usage)
	else:
		handler = bot.commands.get(args[1])

		if handler:
			helptext = "**{}**\n`Uso: {}`\n\n{}".format(handler.name, handler.usage, handler.description)
		else:
			await bot.feedback(message, feedback=navibot.WARNING, text="O comando '{}' não existe".format(args[1]))
			return

	await bot.feedback(message, feedback=navibot.SUCCESS, text=helptext)

async def command_embed(bot, message, args, flags, handler):
	if len(args) < 2 and (not "title" in flags and not "img" in flags):
		await bot.feedback(message, navibot.COMMAND_INFO, text=handler.usage)
		return

	title = ""
	description = ""
	image = ""

	if len(args) > 1:
		description = " ".join(args[1:])

	if "title" in flags:
		title = flags["title"]

	if "img" in flags:
		image = flags["img"]

	embed = discord.Embed(title=title, description=description, color=discord.Colour.purple())
	embed.set_image(url=image)
	embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

	await message.channel.send(embed=embed)
	await bot.feedback(message, navibot.SUCCESS)

async def command_avatar(bot, message, args, flags, handler):
	if len(message.mentions) != 1:
		await bot.feedback(message, navibot.COMMAND_INFO, text=handler.usage)
		return

	user = message.mentions[0]

	embed = discord.Embed(title="Avatar de {}".format(user.name), color=discord.Colour.purple())
	embed.set_image(url=user.avatar_url_as(size=256))
	embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

	await message.channel.send(embed=embed)
	await bot.feedback(message, navibot.SUCCESS)

async def command_remind(bot, message, args, flags, handler):
	if len(args) < 2 and (not "remove" in flags and not "list" in flags) or len(args) > 1 and not "time" in flags:
		await bot.feedback(message, navibot.COMMAND_INFO, text=handler.usage)
		return

	tarefa_str = "{}_reminds".format(str(message.author.id))

	if "list" in flags:
		list_msg = ""

		tarefas = bot.tasks.get(tarefa_str)
		if len(tarefas) > 0:
			for i in range(len(tarefas)):
				data = tarefas[i].kwargs["date"] + datetime.timedelta(seconds=tarefas[i].get_timespan_seconds())
				list_msg += "[{}] `{}`, registrado para {} às {}\n".format(i, tarefas[i].kwargs["remind_text"], data.strftime(r"%d/%m/%Y"), data.strftime(r"%H:%M:%S"))
		else:
			list_msg += "Você não registrou nenhum lembrete até o momento"

		await bot.feedback(message, navibot.SUCCESS, text=list_msg, title="Lembretes ativos")
		return
	elif "remove" in flags:
		tarefas = bot.tasks.get(tarefa_str)

		if len(tarefas) > 0:
			try:
				tarefasel = tarefas[int(flags["remove"])]
				bot.tasks.cancel(tarefasel, tarefa_str)

				await bot.feedback(message, navibot.SUCCESS, text="O lembrete **{}** foi removido".format(tarefasel.kwargs["remind_text"]))
			except ValueError:
				await bot.feedback(message, navibot.WARNING, text="O argumento --remove precisa de um número válido atribuido")
			except IndexError:
				await bot.feedback(message, navibot.WARNING, text="O número do lembrete não existe")
		else:
			await bot.feedback(message, navibot.INFO, text="Você não registrou nenhum lembrete até o momento")
		return

	segundos = 0

	try:
		for tm in re.findall("[0-9]+[hms]", flags["time"]):
			every = re.search("^[0-9]+", tm)
			if every != None:
				every = int(every[0])
			unit = re.search("(h|m|s)$", tm)
			if unit != None:
				unit = unit[0]

			segundos += NaviRoutine.interval_to_seconds((every, unit))
	except ValueError:
		pass

	if segundos == 0:
		await bot.feedback(message, navibot.WARNING, text="O argumento '--time' não está em um formato valido")
		return
	else:
		limite = bot.config.get("commands.descriptions.{}.max_allowed_per_user".format(handler.name))

		if len(bot.tasks.get(tarefa_str)) >= limite:
			await bot.feedback(message, navibot.WARNING, text="Você não pode registrar mais lembretes, pois atingiu o limite máximo de {}".format(limite))
			return
		else:
			task = NaviRoutine(callbackRemind, timespan=(segundos, "s"), waitfor=True, kwargs={"remind_text": " ".join(args[1:]), "date": datetime.datetime.now(), "message": message})
			task.kwargs["task"] = task

			await bot.tasks.schedule(task, key=tarefa_str, append=True)
			await bot.feedback(message, navibot.SUCCESS, text="O lembrete **{}** foi registrado".format(task.kwargs["remind_text"]))
		
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
		playtime=int(json["total_seconds_played"]) / 86400, 
		playcount=json["playcount"], 
		ppraw=json["pp_raw"], 
		accuracy=float(json["accuracy"]), 
		level=float(json["level"]), 
		link="https://" + bot.config.get("external.osu.api_domain") + "/u/" + json["user_id"]
	)

	embed = discord.Embed(title="Perfil de " + json["username"], description=description,color=discord.Colour.magenta())
	embed.set_thumbnail(url="https://" + bot.config.get("external.osu.api_assets") + "/" + json["user_id"])
	embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

	await message.channel.send(embed=embed)
	await bot.feedback(message, navibot.SUCCESS)
