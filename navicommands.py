import discord
import asyncio
import subprocess
import re
import navicallbacks
import navibot
from navilog import LogType
from naviclient import NaviRoutine

# @ NOTE
# Manipuladores de cada comando (são automaticamente detectados ao iniciar com o prefixo 'command_' ou 'command_owner')

# É um command, porém é generico, ou seja, utilizado por outros objetos NaviCommand, portanto não tente adicioná-lo automaticamente utilizando o prefixo generic_ (ao invés de command_)
async def generic_runshell(bot, h, client, message, args, flags):
	# Pega o argumento de execução do nosso handler NaviCommand() acima de nós
	cmdArgs = h.getStaticArgs()
	fullargs = ""

	if len(args) - 1 < cmdArgs["command_cargs"]:
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text=cmdArgs["command_info"])
		return

	if "fullargs" in cmdArgs["command_input"]:
		fullargs = " ".join(args[1:])

	try:
		p = subprocess.run([cmdArgs["command_exec"]] + cmdArgs["command_args"], input=cmdArgs["command_input"].format(args=args, flags=flags, fullargs=fullargs), capture_output=True, encoding="utf-8", timeout=cmdArgs["timeout"])
	except subprocess.TimeoutExpired:
		await bot.sendFeedback(message, navibot.NaviFeedback.WARNING, text="O tempo de limite foi atingido para o subprocesso")
		return
	except Exception:
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

async def command_ping(bot, h, client, message, args, flags):
	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS, text="pong!")

async def command_remind(bot, h, client, message, args, flags):
	if len(args) < 2 or not "time" in flags:
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text="Uso:\nremind <nome_lembrete> [nome_lembrete2...] [--time=[0-9]+(s|m|h)]")
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

	if every == None or unit == None:
		await bot.sendFeedback(message, navibot.NaviFeedback.WARNING, text="O argumento '--time' não está em um formato valido")
		return

	tarefa_str = "{}_{}".format(str(message.author.id), navicallbacks.callbackRemind.__name__)
	tarefa = bot.obterTarefaAgendada(tarefa_str)

	if tarefa == None:
		tarefa = NaviRoutine(bot, navicallbacks.callbackRemind, name=tarefa_str, every=every, unit=unit, canWait=True)
		asyncio.get_running_loop().create_task(bot.agendarTarefa(tarefa, {"remind_text": " ".join(args[1:]), "message": message}))
		await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)
	else:
		await bot.sendFeedback(message, navibot.NaviFeedback.WARNING, text="Recentemente já foi solicitado um 'remind', tente novamente mais tarde")

async def command_embed(bot, h, client, message, args, flags):
	if len(args) < 2 and (not "title" in flags and not "img" in flags):
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text="Uso:\nembed [description] [description2...] [--title=text] [--img=url]")
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
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text="Uso:\navatar <@Usuario>")
		return

	user = message.mentions[0]

	embed = discord.Embed(title="Avatar de {}".format(user.name), color=discord.Colour.purple())
	embed.set_image(url=user.avatar_url_as(size=256))
	embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

	await message.channel.send(embed=embed)
	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)

async def command_osu(bot, h, client, message, args, flags):
	if len(args) < 2:
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text="Uso:\nosu <username> [--mode=std|taiko|ctb|mania]")
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

**Join date:**	{joindate}
**Playtime:** {playtime:.2f} day(s)
**Playcount:**	{playcount}
**PP:**	{ppraw}
**Accuracy:**	{accuracy:.2f}
**Level:**	{level:.2f}

*View on* [osu.ppy.sh]({link})
""".format(rank=json["pp_rank"], country=json["country"].lower(), countryrank=json["pp_country_rank"], joindate=json["join_date"], playtime=int(json["total_seconds_played"]) / 86400, playcount=json["playcount"], ppraw=json["pp_raw"], accuracy=float(json["accuracy"]), level=float(json["level"]), link="https://" + bot.configManager.obter("external.osu.api_domain") + "/u/" + json["user_id"])

	embed = discord.Embed(title="Perfil de " + json["username"], description=description,color=discord.Colour.magenta())
	embed.set_thumbnail(url="https://" + bot.configManager.obter("external.osu.api_assets") + "/" + json["user_id"])
	embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

	await message.channel.send(embed=embed)
	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)

async def command_help(bot, h, client, message, args, flags):
	helptext = "**Comandos disponíveis**\n\n"

	for k in bot.obterCommandHandlers():
		helptext = helptext + "`{}`\n{}\n\n".format(k.getName(), bot.configManager.obter("commands.descriptions.{}".format(k.getName())))

	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS, text=helptext)

async def command_owner_setprefix(bot, h, client, message, args, flags):
	if len(args) < 2 and not "clear" in flags:
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text="Uso:\nsetprefix [prefixo] [--clear]")
		return

	if "clear" in flags:
		bot.botPrefix = bot.configManager.obter("global.bot_prefix")
	else:
		bot.botPrefix = args[1]
	
	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)

async def command_owner_setgame(bot, h, client, message, args, flags):
	if len(args) < 2 and not "clear" in flags:
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text="Uso:\nsetgame [texto] [texto2...] [--clear]")
		return

	task = bot.obterTarefaAgendada(navicallbacks.callbackActivity.__name__)
	
	if task == None:
		await bot.sendFeedback(message, navibot.NaviFeedback.ERROR)
		return
	
	if "clear" in flags:
		asyncio.get_running_loop().create_task(bot.agendarTarefa(task, {"loop": True}))
		await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)
	else:
		task.setIsEnabled(False)

		try:
			await client.change_presence(activity=discord.Game(" ".join(args[1:])))
			await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)
		except Exception:
			await bot.sendFeedback(message, navibot.NaviFeedback.ERROR)

async def command_owner_send(bot, h, client, message, args, flags):
	if len(args) < 3:
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text="Uso:\nsend <channelid> <mensagem> [mensagem2...] [--user]")
		return
	
	c = None

	if not "user" in flags:
		c = client.get_channel(int(args[1]))
	else:
		c = client.get_user(int(args[1]))

	if c != None:
		try:
			await c.send(" ".join(args[2:]))
			await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)
		except Exception as e:
			await bot.sendFeedback(message, navibot.NaviFeedback.ERROR, exception=e)
	else:
		await bot.sendFeedback(message, navibot.NaviFeedback.WARNING, text="O cliente não conseguiu obter o canal/usuário (não tem acesso)")

async def command_owner_argtester(bot, h, client, message, args, flags):
	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS, text="name={}\ncallback={}\nargs={}\nflags={}".format(h.getName(), h.getCallback().__name__, args, flags))

async def command_owner_task(bot, h, client, message, args, flags):
	if len(args) < 2 or (not "enable" in flags and not "disable" in flags):
		if "show" in flags:
			str = ""
			for k in bot.obterTarefasAgendadas():
				str = str + "**{}**\n`callback={},interval={}, enabled={}, isrunning={}, ispersistent={}`\n\n".format(k.getName(), k.getCallback().__name__, k.getInterval(), k.getIsEnabled(), k.getIsRunning(), k.getIsPersistent())

			await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS, text=str)
			return
			
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text="Uso:\ntask [nome_tarefa] [--show] [--enable] [--disable]")
		return

	tarefa = bot.obterTarefaAgendada(args[1])

	if tarefa == None:
		await bot.sendFeedback(message, navibot.NaviFeedback.WARNING, text="A tarefa não foi encontrada")
		return

	if "enable" in flags:
		if not tarefa.getIsEnabled():
			asyncio.get_running_loop().create_task(bot.agendarTarefa(tarefa, {"loop": True}))
	else:
		tarefa.setIsEnabled(False)

	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS)

# @SECTION
# Comandos disponibilizados para a CLI oferecida pelo bot

async def cli_echo(bot, h, client, message, args, flags):
	bot.logManager.write(" ".join(args[1:]), logtype=LogType.DEBUG)

async def cli_select(bot, h, client, message, args, flags):
	if len(args) < 2 and not "show" in flags:
		bot.logManager.write("Uso:\nselect <channelid> [--user] [--show]", logtype=LogType.DEBUG)
		return

	if "show" in flags:
		if bot.cliSelectedChannel == None:
			bot.logManager.write("Nenhum canal/usuário está selecionado", logtype=LogType.DEBUG)
		elif type(bot.cliSelectedChannel) == discord.User:
			bot.logManager.write("O usuário selecionado é: {} ({})".format(bot.cliSelectedChannel.name, bot.cliSelectedChannel.id), logtype=LogType.DEBUG)
		elif type(bot.cliSelectedChannel) == discord.TextChannel:
			bot.logManager.write("O canal selecionado é: {}#{} ({})".format(bot.cliSelectedChannel.guild.name, bot.cliSelectedChannel.name, bot.cliSelectedChannel.id), logtype=LogType.DEBUG)
		else:
			bot.logManager.write("O canal selecionado é: {}".format(str(bot.cliSelectedChannel)), logtype=LogType.DEBUG)

		return

	try:
		cid = int(args[1])
	except Exception:
		bot.logManager.write("O id informado não é um número", logtype=LogType.DEBUG)
		return

	if "user" in flags:
		bot.cliSelectedChannel = client.get_user(cid)
	else:
		bot.cliSelectedChannel = client.get_channel(cid)

	if bot.cliSelectedChannel == None or (type(bot.cliSelectedChannel) != discord.TextChannel and type(bot.cliSelectedChannel) != discord.User):
		bot.logManager.write("O id informado não é um canal/usuário válido", logtype=LogType.DEBUG)
	else:
		await cli_select(bot, h, client, message, [], {"show": True})

async def cli_say(bot, h, client, message, args, flags):
	if len(args) < 2:
		bot.logManager.write("Uso:\nsay <mensagem> [mensagem2...]", logtype=LogType.DEBUG)
		return

	if bot.cliSelectedChannel == None:
		bot.logManager.write("Nenhum canal foi selecionado para enviar a mensagem, selecione utilizando o comando 'select'", logtype=LogType.DEBUG)
		return

	try:
		await bot.cliSelectedChannel.send(" ".join(args[1:]))
	except Exception as e:
		bot.logManager.write(str(e), LogType.ERROR)

async def cli_quit(bot, h, client, message, args, flags):
	bot.logManager.write("Desligando o cliente...", logtype=LogType.WARNING)
	bot.logManager.setAtivado(False)
	bot.logManager.fechar()
	await bot.httpClientSession.close()
	await bot.fechar()
