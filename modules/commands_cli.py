import discord
import navilog

# @SECTION
# Comandos disponibilizados para a CLI oferecida pelo bot

async def cli_help(bot, message, args, flags, handler):
	for key in bot.clicommands.get_commands().keys():
		bot.log.write(bot.clicommands.get(key).usage, logtype=navilog.DEBUG)

async def cli_echo(bot, message, args, flags, handler):
	bot.log.write(" ".join(args[1:]), logtype=navilog.DEBUG)

async def cli_context(bot, message, args, flags, handler):
	if len(args) < 2 and (not "show" in flags and not "clear" in flags):
		bot.logManager.write(handler.usage, logtype=navilog.DEBUG)
		return

	if "show" in flags:
		if bot.cli_context == None:
			bot.log.write("Nenhum contexto está selecionado", logtype=navilog.DEBUG)

			for g in bot.client.guilds:
				bot.log.write("{} ({})".format(g.name, g.id), logtype=navilog.DEBUG)

		elif isinstance(bot.cli_context, discord.User):
			bot.log.write("O usuário selecionado é: {} ({})".format(bot.cli_context.name, bot.cli_context.id), logtype=navilog.DEBUG)
		elif isinstance(bot.cli_context, discord.TextChannel):
			bot.log.write("O canal selecionado é: {}#{} ({})".format(bot.cli_context.guild.name, bot.cli_context.name, bot.cli_context.id), logtype=navilog.DEBUG)
		elif isinstance(bot.cli_context, discord.Guild):
			bot.log.write("A guild selecionada é: {} ({})".format(bot.cli_context.name, bot.cli_context.id), logtype=navilog.DEBUG)

			for g in bot.cli_context.channels:
				if isinstance(g, discord.TextChannel):
					bot.log.write("#{} ({})".format(g.name, g.id), logtype=navilog.DEBUG)
		else:
			bot.log.write("O contexto selecionado é: {}".format(str(bot.cli_context)), logtype=navilog.DEBUG)

		return
	elif "clear" in flags:
		bot.cli_context = None
		return

	try:
		cid = int(args[1])
	except Exception:
		bot.log.write("O id informado não é um número", logtype=navilog.DEBUG)
		return

	if "u" in flags:
		bot.cli_context = bot.client.get_user(cid)
	elif "c" in flags:
		bot.cli_context = bot.client.get_channel(cid)
	elif "g" in flags:
		bot.cli_context = bot.client.get_guild(cid)
	else:
		bot.log.write(handler.usage, logtype=navilog.DEBUG)
		return

	await cli_context(bot, message, args, {"show": True}, handler)

async def cli_say(bot, message, args, flags, handler):
	if len(args) < 2:
		bot.log.write(handler.usage, logtype=navilog.DEBUG)
		return

	if (not isinstance(bot.cli_context, discord.TextChannel)) and (not isinstance(bot.cli_context, discord.User)):
		bot.log.write("Nenhum canal foi selecionado para enviar a mensagem, selecione utilizando o comando 'context'", logtype=navilog.DEBUG)
		return

	try:
		await bot.cli_context.send(" ".join(args[1:]))
	except Exception as e:
		bot.handle_exception(e)

async def cli_task(bot, message, args, flags, handler):
	# @TODO:
	# Efetuar implementação dos métodos de manipulação de tarefas...
	if not "list" in flags:
		bot.log.write(handler.usage, logtype=navilog.DEBUG)

	if "list" in flags:
		for key in bot.tasks.get_all_keys():
			taskstr = f"[{key}]: {{"
			for task in bot.tasks.get(key):
				taskstr += f"{str(task)} "
			taskstr += "}"

			bot.log.write(taskstr, logtype=navilog.DEBUG)
	else:
		pass

async def cli_event(bot, message, args, flags, handler):
	if not "list" in flags:
		bot.log.write(handler.usage, logtype=navilog.DEBUG)

	if "list" in flags:
		for key in bot.client.get_all_keys():
			eventstr = f"[{key}]: {{"
			for callback in bot.client.get_callbacks_from(key):
				eventstr += f"{str(callback)} "
			eventstr += "}"

			bot.log.write(eventstr, logtype=navilog.DEBUG)
	else:
		pass

async def cli_quit(bot, message, args, flags, handler):
	bot.log.write("Desligando o cliente...", logtype=navilog.WARNING)
	await bot.stop()

async def cli_reload(bot, message, args, flags, handler):
	bot.log.write("Recarregando modulos...", logtype=navilog.WARNING)
	bot.initialize()