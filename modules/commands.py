import discord
import re
import datetime
import navibot
from naviclient import NaviRoutine
from navibot import EmbedSlideItem
from navibot import EmbedSlide

async def callbackRemind(bot, kwargs):
	message = kwargs["message"]
	task = kwargs["task"]
	remind_text = kwargs["remind_text"]

	task.enabled = False

	await message.author.send(f"Olá <@{message.author.id}>, estou te enviando um lembrete para: **{remind_text}**")

# @SECTION
# Comandos disponibilizados por padrão pelo bot

async def command_owner_setconfig(bot, message, args, flags, handler):
	if len(args) < 3:
		await bot.feedback(message, navibot.COMMAND_INFO, text=handler.usage)
		return

	if bot.config.set(args[1], " ".join(args[2:])):
		await bot.feedback(message, navibot.SUCCESS)
	else:
		await bot.feedback(message, navibot.ERROR, text=f"A chave **{args[1]}**' não foi encontrada")

async def command_help(bot, message, args, flags, handler):
	if len(args) < 2:
		helptext = "**Comandos disponíveis**\n\n"

		for key in bot.commands.get_commands().keys():
			helptext += f"**{key}**\n`{bot.commands.get(key).usage}`\n\n"
	else:
		handler = bot.commands.get(args[1])

		if handler:
			helptext = f"**{handler.name}**\n`Uso: {handler.usage}`\n\n{handler.description}"
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

	tarefa_str = f"{message.author.id}_reminds"

	tarefas = bot.tasks.get(tarefa_str)

	if "list" in flags:
		list_msg = ""

		if tarefas:
			for i in range(len(tarefas)):
				data = tarefas[i].kwargs["date"] + datetime.timedelta(seconds=tarefas[i].get_timespan_seconds())
				list_msg += "[{}] `{}`, registrado para {} às {}\n".format(i, tarefas[i].kwargs["remind_text"], data.strftime(r"%d/%m/%Y"), data.strftime(r"%H:%M:%S"))
		else:
			list_msg += "Você não registrou nenhum lembrete até o momento"

		await bot.feedback(message, navibot.SUCCESS, text=list_msg, title="Lembretes ativos")
	elif "remove" in flags:
		if tarefas:
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
	else:
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

			if tarefas and len(tarefas) >= limite:
				await bot.feedback(message, navibot.WARNING, text="Você não pode registrar mais lembretes, pois atingiu o limite máximo de {}".format(limite))
			else:
				task = NaviRoutine(callbackRemind, timespan=(segundos, "s"), waitfor=True, kwargs={"remind_text": " ".join(args[1:]), "date": datetime.datetime.now(), "message": message})
				task.kwargs["task"] = task

				bot.tasks.schedule(task, key=tarefa_str, append=True)
				await bot.feedback(message, navibot.SUCCESS, text="O lembrete **{}** foi registrado".format(task.kwargs["remind_text"]))
