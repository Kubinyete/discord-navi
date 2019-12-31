import discord
import re
import datetime
import random
import navibot
from naviclient import NaviRoutine
from navibot import EmbedItem
from navibot import EmbedSlide

async def callbackRemind(bot, kwargs):
	message = kwargs["message"]
	task = kwargs["task"]
	remind_text = kwargs["remind_text"]

	task.enabled = False

	await message.author.send(f"Olá <@{message.author.id}>, estou te enviando um lembrete para: **{remind_text}**")

# @SECTION
# Comandos disponibilizados por padrão pelo bot

async def command_help(bot, message, args, flags, handler):
	if len(args) < 2:
		helptext = "**Comandos disponíveis**\n\n"

		for key in bot.commands.get_commands().keys():
			handler = bot.commands.get(key)

			if bot.is_owner(message.author) or not handler.owneronly:
				if isinstance(handler.usage, list):
					usagef = "\n".join([f"`{key} {i}`" for i in handler.usage])
				else:
					usagef = f"`{key} {handler.usage}`"

				helptext += f"**{key}**\n{usagef}\n\n"
	else:
		handler = bot.commands.get(args[1])

		if handler and (bot.is_owner(message.author) or not handler.owneronly):
			if isinstance(handler.usage, list):
				usagef = "\n".join([f"`{args[1]} {i}`" for i in handler.usage])
			else:
				usagef = f"{args[1]} `{handler.usage}`"

			helptext = f"**{handler.name}**\n{usagef}\n\n{handler.description}"
		else:
			await bot.feedback(message, feedback=navibot.WARNING, text=f"O comando '{args[1]}' não existe.")
			return

	await bot.feedback(message, feedback=navibot.SUCCESS, text=helptext)

async def command_roll(bot, message, args, flags, handler):
	rollmin = 1
	rollmax = 6

	try:
		if len(args) > 2:
			rollmin = int(args[1])
			rollmax = int(args[2])
		elif len(args) > 1:
			rollmax = int(args[1])
	except ValueError:
		await bot.feedback(message, feedback=navibot.WARNING, text="É preciso informar números válidos.")
		return

	if rollmax < rollmin:
		await bot.feedback(message, feedback=navibot.WARNING, text=f"A faixa de valores {rollmin} - {rollmax} informada precisa ser válida.")
	else:
		await bot.feedback(message, feedback=navibot.SUCCESS, text=f"**{message.author.name}** girou o número {random.randint(rollmin, rollmax)}.")

async def command_avatar(bot, message, args, flags, handler):
	if len(message.mentions) != 1:
		await bot.feedback(message, navibot.COMMAND_INFO, usage=handler)
		return

	user = message.mentions[0]

	embed = discord.Embed(title="Avatar de {}".format(user.name), color=discord.Colour.purple())
	embed.set_image(url=user.avatar_url_as(size=256))
	embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

	await message.channel.send(embed=embed)
	await bot.feedback(message, navibot.SUCCESS)

async def command_remind(bot, message, args, flags, handler):
	if len(args) < 2 and (not "remove" in flags and not "list" in flags) or len(args) > 1 and not "time" in flags:
		await bot.feedback(message, navibot.COMMAND_INFO, usage=handler)
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
		else:
			limite = bot.config.get("commands.descriptions.{}.max_allowed_per_user".format(handler.name))

			if tarefas and len(tarefas) >= limite:
				await bot.feedback(message, navibot.WARNING, text="Você não pode registrar mais lembretes, pois atingiu o limite máximo de {}".format(limite))
			else:
				task = NaviRoutine(callbackRemind, timespan=(segundos, "s"), waitfor=True, kwargs={"remind_text": " ".join(args[1:]), "date": datetime.datetime.now(), "message": message})
				task.kwargs["task"] = task

				bot.tasks.schedule(task, key=tarefa_str, append=True)
				await bot.feedback(message, navibot.SUCCESS, text="O lembrete **{}** foi registrado".format(task.kwargs["remind_text"]))
