import discord
import asyncio
import subprocess
import re
import navicallbacks
import navibot
from datetime import datetime
from datetime import timedelta
from navilog import LogType
from naviclient import NaviRoutine

# @ NOTE
# Manipuladores de cada comando (são automaticamente detectados ao iniciar com o prefixo 'command_' ou 'command_owner')

# É um command, porém é generico, ou seja, utilizado por outros objetos NaviCommand, portanto não tente adicioná-lo automaticamente utilizando o prefixo generic_ (ao invés de command_)
async def generic_runshell(bot, h, client, message, args, flags):
	# Pega o argumento de execução do nosso handler NaviCommand() acima de nós
	cmdArgs = h.getStaticArgs()
	fullargs = ""

	qtdArgs = 0

	for m in re.findall(r"{args\[[0-9]+\]}", cmdArgs["command_input"]):
		i = int(re.search(r"[0-9]+", m)[0])

		if i > qtdArgs:
			qtdArgs = i

	for m in re.findall(r"{args\[[0-9]+\]}", cmdArgs["command_exec_args"]):
		i = int(re.search(r"[0-9]+", m)[0])

		if i > qtdArgs:
			qtdArgs = i

	if len(args) - 1< qtdArgs:
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text=cmdArgs["command_info"])
		return

	if "fullargs" in cmdArgs["command_input"]:
		fullargs = " ".join(args[1:])

	try:
		p = subprocess.run("{} {}".format(cmdArgs["command_exec"], cmdArgs["command_exec_args"].format(args=args, flags=flags, fullargs=fullargs)), input=cmdArgs["command_input"].format(args=args, flags=flags, fullargs=fullargs), shell=True, capture_output=True, encoding="utf-8", timeout=cmdArgs["timeout"])
	except subprocess.TimeoutExpired:
		await bot.sendFeedback(message, navibot.NaviFeedback.WARNING, text="O tempo de limite foi atingido para o subprocesso")
		return
	except Exception as e:
		await bot.sendFeedback(message, navibot.NaviFeedback.ERROR, exception=e)
		return

	if len(p.stdout) > 2000:
		await bot.sendFeedback(message, navibot.NaviFeedback.WARNING, text="O conteudo resultante é muito grande, por favor insira um texto menor")
		return
	elif len(p.stdout) < 1:
		if len(p.stderr) > 0:
			await bot.sendFeedback(message, navibot.NaviFeedback.WARNING, text=p.stderr)
			return

		await bot.sendFeedback(message, navibot.NaviFeedback.WARNING, text="Nenhum conteúdo resultante")
		return

	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS, code=True, text=p.stdout)
	return

async def command_help(bot, h, client, message, args, flags):
	helptext = ""

	if len(args) < 2:
		helptext = "**Comandos disponíveis**\n\n"

		for k in bot.obterCommandHandlers():
			helptext = helptext + "`{}`\n{}\n\n".format(k.getName(), k.getDescription())
	else:
		handler = bot.obterComando(args[1])

		if handler:
			helptext = "**{}**\n`Uso: {}`\n\n{}".format(handler.getName(), handler.getUsage(), handler.getDescription())
		else:
			await bot.sendFeedback(message, navibot.NaviFeedback.WARNING, text="O comando '{}' não existe".format(args[1]))
			return

	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS, text=helptext)

async def command_remind(bot, h, client, message, args, flags):
	if len(args) < 2 and not "list" in flags or not "list" in flags and not "time" in flags:
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text=h.getUsage())
		return

	if "list" in flags:
		tarefa_str = "{}_{}".format(str(message.author.id), navicallbacks.callbackRemind.__name__)
		tarefa = bot.obterTarefaAgendada(tarefa_str)

		if tarefa:
			await bot.sendFeedback(message, navibot.NaviFeedback.INFO, text="'**{}**', solicitado em ***{}*** para expirar em ***{}***".format(tarefa.getStaticArgs()['remind_text'], tarefa.getStaticArgs()['remind_date'].strftime("%d/%m/%Y às %H:%M:%S"), (tarefa.getStaticArgs()['remind_date'] + timedelta(seconds=tarefa.getIntervalInSeconds())).strftime("%d/%m/%Y às %H:%M:%S")))
		else:
			await bot.sendFeedback(message, navibot.NaviFeedback.INFO, text="Você não registrou nenhum remind até o momento")

		return

	try:
		every = re.search("^[0-9]+", flags["time"])
		if every != None:
			every = int(every[0])
		unit = re.search("(h|m|s)$", flags["time"])
		if unit != None:
			unit = unit[0]
	except Exception as e:
		await bot.sendFeedback(message, navibot.NaviFeedback.ERROR, exception=e)
		return

	if every == None or unit == None or every == 0:
		await bot.sendFeedback(message, navibot.NaviFeedback.WARNING, text="O argumento '--time' não está em um formato valido")
		return

	tarefa_str = "{}_{}".format(str(message.author.id), navicallbacks.callbackRemind.__name__)
	tarefa = bot.obterTarefaAgendada(tarefa_str)

	if tarefa == None:
		tarefa = NaviRoutine(bot, navicallbacks.callbackRemind, name=tarefa_str, every=every, unit=unit, canWait=True, staticArgs={"remind_text": " ".join(args[1:]), "remind_date": datetime.now(), "message": message})
		await bot.agendarTarefa(tarefa)
		await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)
	else:
		await bot.sendFeedback(message, navibot.NaviFeedback.WARNING, text="Recentemente já foi solicitado um 'remind', tente novamente mais tarde")

async def command_embed(bot, h, client, message, args, flags):
	if len(args) < 2 and (not "title" in flags and not "img" in flags):
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text=h.getUsage())
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
	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)

async def command_avatar(bot, h, client, message, args, flags):
	if len(message.mentions) != 1:
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text=h.getUsage())
		return

	user = message.mentions[0]

	embed = discord.Embed(title="Avatar de {}".format(user.name), color=discord.Colour.purple())
	embed.set_image(url=user.avatar_url_as(size=256))
	embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

	await message.channel.send(embed=embed)
	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)

async def command_osu(bot, h, client, message, args, flags):
	if len(args) < 2:
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text=h.getUsage())
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
		json = await bot.fetchJson("https://" + bot.configManager.obter("external.osu.api_domain") + bot.configManager.obter("external.osu.api_getuser"), {"k": bot.configManager.obter("external.osu.api_key"), "u": " ".join(args[1:]), "m": modeid, "type": "string"})

		if len(json) > 0:
			json = json[0]
		else:
			await bot.sendFeedback(message, navibot.NaviFeedback.WARNING, text="Não foi encontrado nenhum usuário com esse nome")
			return
	except Exception as e:
		await bot.sendFeedback(message, navibot.NaviFeedback.ERROR, exception=e)
		return

	description = """
**#{rank}** (:flag_{country}: **#{countryrank}**)

**Join date:** {joindate}
**Playtime:** {playtime:.2f} day(s)
**Playcount:** {playcount}
**PP:** {ppraw}
**Accuracy:** {accuracy:.2f}
**Level:** {level:.2f}

*View on* [osu.ppy.sh]({link})
""".format(rank=json["pp_rank"], country=json["country"].lower(), countryrank=json["pp_country_rank"], joindate=json["join_date"], playtime=int(json["total_seconds_played"]) / 86400, playcount=json["playcount"], ppraw=json["pp_raw"], accuracy=float(json["accuracy"]), level=float(json["level"]), link="https://" + bot.configManager.obter("external.osu.api_domain") + "/u/" + json["user_id"])

	embed = discord.Embed(title="Perfil de " + json["username"], description=description,color=discord.Colour.magenta())
	embed.set_thumbnail(url="https://" + bot.configManager.obter("external.osu.api_assets") + "/" + json["user_id"])
	embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

	await message.channel.send(embed=embed)
	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)

async def command_owner_setprefix(bot, h, client, message, args, flags):
	if len(args) < 2 and not "clear" in flags:
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text=h.getUsage())
		return

	if "clear" in flags:
		bot.botPrefix = bot.configManager.obter("global.bot_prefix")
	else:
		bot.botPrefix = args[1]
	
	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)

async def command_owner_setgame(bot, h, client, message, args, flags):
	if len(args) < 2 and not "clear" in flags:
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text=h.getUsage())
		return

	task = bot.obterTarefaAgendada(navicallbacks.callbackActivity.__name__)
	
	if task == None:
		await bot.sendFeedback(message, navibot.NaviFeedback.ERROR)
		return
	
	if "clear" in flags:
		await bot.agendarTarefa(task, {"loop": True})

		await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)
	else:
		task.setIsEnabled(False)

		try:
			await client.change_presence(activity=discord.Game(" ".join(args[1:])))
			await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)
		except Exception:
			await bot.sendFeedback(message, navibot.NaviFeedback.ERROR)

# @SECTION
# Comandos disponibilizados para a CLI oferecida pelo bot

async def cli_help(bot, h, client, message, args, flags):
	for k in bot.obterCliHandlers():
		bot.logManager.write(k.getUsage(), logtype=LogType.DEBUG)

async def cli_echo(bot, h, client, message, args, flags):
	bot.logManager.write(" ".join(args[1:]), logtype=LogType.DEBUG)

# @REWRITE: Atualizar a forma de interagir com chats de diferentes servidores via CLI, atualmente não está muito prático
async def cli_context(bot, h, client, message, args, flags):
	if len(args) < 2 and (not "show" in flags and not "clear" in flags):
		bot.logManager.write(h.getUsage(), logtype=LogType.DEBUG)
		return

	if "show" in flags:
		if bot.cliContext == None:
			bot.logManager.write("Nenhum contexto está selecionado", logtype=LogType.DEBUG)

			for g in client.guilds:
				bot.logManager.write("{} ({})".format(g.name, g.id), logtype=LogType.DEBUG)

		elif type(bot.cliContext) == discord.User:
			bot.logManager.write("O usuário selecionado é: {} ({})".format(bot.cliContext.name, bot.cliContext.id), logtype=LogType.DEBUG)
		elif type(bot.cliContext) == discord.TextChannel:
			bot.logManager.write("O canal selecionado é: {}#{} ({})".format(bot.cliContext.guild.name, bot.cliContext.name, bot.cliContext.id), logtype=LogType.DEBUG)
		elif type(bot.cliContext) == discord.Guild:
			bot.logManager.write("A guild selecionada é: {} ({})".format(bot.cliContext.name, bot.cliContext.id), logtype=LogType.DEBUG)

			for g in bot.cliContext.channels:
				if type(g) == discord.TextChannel:
					bot.logManager.write("#{} ({})".format(g.name, g.id), logtype=LogType.DEBUG)
		else:
			bot.logManager.write("O contexto selecionado é: {}".format(str(bot.cliContext)), logtype=LogType.DEBUG)

		return
	elif "clear" in flags:
		bot.cliContext = None
		return

	try:
		cid = int(args[1])
	except Exception:
		bot.logManager.write("O id informado não é um número", logtype=LogType.DEBUG)
		return

	if "u" in flags:
		bot.cliContext = client.get_user(cid)
	elif "c" in flags:
		bot.cliContext = client.get_channel(cid)
	elif "g" in flags:
		bot.cliContext = client.get_guild(cid)
	else:
		bot.logManager.write(h.getUsage(), logtype=LogType.DEBUG)
		return

	await cli_context(bot, h, client, message, [], {"show": True})

# @REWRITE: Atualizar a forma de interagir com chats de diferentes servidores via CLI, atualmente não está muito prático
async def cli_say(bot, h, client, message, args, flags):
	if len(args) < 2:
		bot.logManager.write(h.getUsage(), logtype=LogType.DEBUG)
		return

	if type(bot.cliContext) != discord.TextChannel:
		bot.logManager.write("Nenhum canal foi selecionado para enviar a mensagem, selecione utilizando o comando 'context'", logtype=LogType.DEBUG)
		return

	try:
		await bot.cliContext.send(" ".join(args[1:]))
	except Exception as e:
		bot.logManager.write(str(e), LogType.ERROR)

async def cli_task(bot, h, client, message, args, flags):
	if len(args) < 2 and not "list" in flags:
		bot.logManager.write(h.getUsage(), logtype=LogType.DEBUG)
		return

	if "list" in flags:
		for t in bot.obterTarefasAgendadas():
			bot.logManager.write("['{}']: callback={}, name={}, staticArgs={}, canWait={}, isEnabled={}, interval={}, intervalSeconds={}, isRunning={}, isPersistent={}".format(t.getName(), t.getCallback().__name__, t.getName(), t.getStaticArgs(), t.getCanWait(), t.getIsEnabled(), t.getInterval(), t.getIntervalInSeconds(), t.getIsRunning(), t.getIsPersistent()), logtype=LogType.DEBUG)

		return

	task = bot.obterTarefaAgendada(args[1])

	if task == None:
		bot.logManager.write("Não foi possível encontrar a tarefa '{}'".format(args[1]), logtype=LogType.DEBUG)
		return

	if "enable" in flags:
		await bot.agendarTarefa(task, {"loop": True})
	else:
		task.setIsEnabled(False)

	await cli_task(bot, h, client, message, [], {"list": True})

async def cli_quit(bot, h, client, message, args, flags):
	bot.logManager.write("Desligando o cliente...", logtype=LogType.WARNING)
	bot.logManager.setAtivado(False)
	bot.logManager.fechar()
	await bot.httpClientSession.close()
	await bot.fechar()

async def cli_reload(bot, h, client, message, args, flags):
	bot.logManager.write("Recarregando modulos...", logtype=LogType.WARNING)
	bot.recarregar()
