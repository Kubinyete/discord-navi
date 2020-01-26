import discord
import re
import datetime
import random
import navibot
import naviuteis
from naviclient import NaviRoutine
from navibot import EmbedItem
from navibot import EmbedSlide
from navibot import Poll

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
		naviabout = bot.config.get(f"commands.{handler.name}.navi_about")

		helptext = f":information_source: Digite `{bot.prefix}{handler.name} [comando]` para obter mais informações\n\n**Comandos disponíveis**:\n"

		currentmdl = ""
		for key in bot.commands.get_commands().keys():
			handler = bot.commands.get(key)

			if bot.is_owner(message.author) or not handler.owneronly:
				if currentmdl != handler.callback.__module__:
					helptext += f"\n{handler.callback.__module__}\n"
					currentmdl = handler.callback.__module__

				helptext += f"* `{key}`\n"

		embeditem = EmbedItem(
			title=f"NaviBot",
			description=f"{naviabout}\n\n{helptext}",
			footer=(
				message.author.name, 
				message.author.avatar_url_as(size=32)
			)
		)

		await bot.feedback(message, feedback=navibot.SUCCESS, embeditem=embeditem)
	else:
		handler = bot.commands.get(args[1])

		if handler and (bot.is_owner(message.author) or not handler.owneronly):
			if isinstance(handler.usage, list):
				usagef = "\n".join([f"`{args[1]} {i}`" for i in handler.usage])
			else:
				usagef = f"`{args[1]} {handler.usage}`"

			helptext = f"**{handler.name}**\n{handler.description}\n\nUso:\n{usagef}"
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
		await bot.feedback(message, feedback=navibot.SUCCESS, text=f"{random.randint(rollmin, rollmax)}")

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
		segundos = naviuteis.get_time_from(flags["time"])

		if segundos == 0:
			await bot.feedback(message, navibot.WARNING, text="O argumento '--time' não está em um formato valido")
		else:
			limite = bot.config.get(f"commands.{handler.name}.max_allowed_per_user")
			if not limite:
				limite = 5

			if tarefas and len(tarefas) >= limite:
				await bot.feedback(message, navibot.WARNING, text="Você não pode registrar mais lembretes, pois atingiu o limite máximo de {}".format(limite))
			else:
				task = NaviRoutine(callbackRemind, timespan=(segundos, "s"), waitfor=True, kwargs={"remind_text": " ".join(args[1:]), "date": datetime.datetime.now(), "message": message})
				task.kwargs["task"] = task

				bot.tasks.schedule(task, key=tarefa_str, append=True)
				await bot.feedback(message, navibot.SUCCESS)

async def command_poll(bot, message, args, flags, handler):
	if len(args) < 4:
		await bot.feedback(message, navibot.COMMAND_INFO, usage=handler)
		return

	question = args[1]
	answers = args[2:]

	limit = bot.config.get(f"commands.{handler.name}.max_allowed_answers")
	if not limit:
		limit = 6

	if len(answers) < 2:
		await bot.feedback(message, navibot.WARNING, text="É preciso informar no mínimo duas respostas para iniciar a votação")
	elif len(answers) > limit:
		await bot.feedback(message, navibot.WARNING, text=f"O número de respostas informado ultrapassa o limite estabelecido de {limit}")
	else:
		seconds = 60

		if "time" in flags:
			seconds = naviuteis.get_time_from(flags["time"])

		if seconds < 10:
			await bot.feedback(message, navibot.WARNING, text="O tempo específicado é menor que 10 segundos")
		elif seconds > naviuteis.timespan_to_seconds((24, "h")):
			await bot.feedback(message, navibot.WARNING, text="O tempo específicado é maior que 24 horas")
		else:
			p = Poll(question, answers, message, timeout=seconds)
			await p.send_and_wait(bot)

async def command_config(bot, message, args, flags, handler):
	currsettings = await bot.guildsettings.get_settings(message.guild)

	if len(args) < 2:
		items = []
		
		per_page = bot.config.get(f"commands.{handler.name}.max_allowed_settings_per_page")
		if not per_page:
			per_page = 10

		i = 0
		curritem = EmbedItem(
			title="Chaves de configuração da Guild",
		)

		for key, value in currsettings.items():
			curritem.description += f'`{key}` = {discord.utils.escape_markdown(str(value))}\n'
			i += 1

			if i % per_page == 0:
				items.append(curritem)
				curritem = EmbedItem(
					title="Chaves de configuração da Guild",
				)

		if i % per_page != 0:
			items.append(curritem)

		if i > 0:
			await EmbedSlide(items, message).send_and_wait(bot)
		else:
			await bot.feedback(message, feedback=navibot.WARNING, text=f"Nenhuma chave foi encontrada para esta guild")
	else:
		if len(args) > 2 and args[1] == "get":
			try:
				await bot.feedback(message, feedback=navibot.SUCCESS, text=f'`{args[2]}` = {discord.utils.escape_markdown(str(currsettings[args[2]]))}\n')
			except KeyError:
				await bot.feedback(message, feedback=navibot.WARNING, text=f"A chave `{args[2]}` não foi encontrada")
		elif len(args) > 3 and args[1] == "set":
			if not args[2] in currsettings:
				await bot.feedback(message, feedback=navibot.WARNING, text=f"A chave `{args[2]}` não foi encontrada")
			else:
				oldvalue = currsettings[args[2]]
				newvalue = naviuteis.convert_string_any_type(" ".join(args[3:]))

				if type(oldvalue) != type(newvalue):
					await bot.feedback(message, feedback=navibot.WARNING, text=f"A chave `{args[2]}` precisa ser do tipo `{type(oldvalue).__name__}`")
				else:
					currsettings[args[2]] = newvalue

					try:
						await bot.guildsettings.update_settings(message.guild, currsettings)
						await bot.feedback(message, feedback=navibot.SUCCESS)
					except Exception as e:
						await bot.feedback(message, feedback=navibot.ERROR, exception=e)
		else:
			await bot.feedback(message, feedback=navibot.COMMAND_INFO, usage=handler)