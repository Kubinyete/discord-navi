import discord
import asyncio
import re
import sys
import select
import naviuteis
from navilog import LogType
from naviclient import NaviRoutine

# @NOTE
# Esse modulo fica responsável por servir de container para um set de comandos no qual a classe principal NaviBot irá examinar e referenciar as funções que estão aqui

async def callbackLog(navibot, client, rotinaOrigem, runtimeArgs):
	message = runtimeArgs["message"]

	if not message:
		navibot.logManager.write("O bot foi iniciado com sucesso")
	else:
		navibot.logManager.write(message, logtype=LogType.MESSAGE)

async def callbackActivity(navibot, client, rotinaOrigem, runtimeArgs):
	if not "loop" in runtimeArgs:
		await navibot.agendarTarefa(NaviRoutine(navibot, callbackActivity, every=navibot.configManager.obter("global.bot_playing_delay"), unit="s", isPersistent=True), {"loop": True})
		return

	activities = navibot.configManager.obter("global.bot_playing")

	if activities != None:
		if navibot.botPlayingIndex >= len(activities):
			navibot.botPlayingIndex = 0

		await navibot.naviClient.change_presence(activity=discord.Game(activities[navibot.botPlayingIndex]))

		navibot.botPlayingIndex = navibot.botPlayingIndex + 1

async def callbackCommandHandler(navibot, client, rotinaOrigem, runtimeArgs):
	message = runtimeArgs["message"]

	# @NOTE
	# callbackCommandHandler() só aceita mensagens direcionadas ao bot e que não são diretamente de outro bot (pode causar um loop infinito)
	if message.author == client.user or message.author.bot:
		return

	if message.content.startswith(navibot.botPrefix):
		args, flags = naviuteis.listarArgumentos(message.content[len(navibot.botPrefix):])

		if len(args) > 0:
			asyncio.get_running_loop().create_task(navibot.interpretarComando(client, message, args, flags))

async def callbackCliListener(navibot, client, rotinaOrigem, runtimeArgs):
	if not navibot.cliEnabled:
		return

	if not "loop" in runtimeArgs.keys():
		await navibot.agendarTarefa(NaviRoutine(navibot, callbackCliListener, every=navibot.configManager.obter("cli.update_delay"), unit="ms", isPersistent=True), {"loop": True})
		return

	clilines = []

	# @BUG
	# Apenas funciona no Linux, ler da entrada padrão sem travar a thread principal é bem chato no Python e as funções principais ficam esperando ou newline ou EOF
	# Por enquanto a CLI só ficará disponível pelo Linux
	# 
	# Para entender o que está acontecendo:
	# Enquanto STDIN estiver disponível para leitura (tem algo no buffer), leia a linha presente (normalmente os terminais só enviam a linha quando o usuário aperta ENTER)
	# while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
	# 	clilines.append(re.sub(r"\n", r"", sys.stdin.readline()))

	# for l in clilines:
	# 	cliargs, cliflags = naviuteis.listarArgumentos(l)

	# 	if len(cliargs) > 0:
	# 		# @NOTE:
	# 		# Usando await pois queremos que cada comando na CLI seja sequencial
	# 		await navibot.interpretarComandoCli(client, cliargs, cliflags)

	while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
		c = sys.stdin.read(1)

		if c == '\n':
			if len(navibot.cliBuffer) > 0:
				clilines.append(navibot.cliBuffer)
				navibot.logManager.desenharInput(True)
				navibot.cliBuffer = ""
		elif c == '\x7f':
			if len(navibot.cliBuffer) > 0:
				navibot.cliBuffer = navibot.cliBuffer[:-1]
		elif c == '\x1b':
			# navibot.logManager.write("Pegou um caractere SEQUENCIAL", LogType.DEBUG)
			pass
		else:
			navibot.cliBuffer = navibot.cliBuffer + c
		
		navibot.logManager.desenharInput()
		
	for l in clilines:
		cliargs, cliflags = naviuteis.listarArgumentos(l)

		if len(cliargs) > 0:
			# @NOTE:
			# Usando await pois queremos que cada comando na CLI seja sequencial
			await navibot.interpretarComandoCli(client, cliargs, cliflags)
			# asyncio.get_running_loop().create_task(navibot.interpretarComandoCli(client, cliargs, cliflags))

async def callbackRemind(navibot, client, rotinaOrigem, runtimeArgs):
	stargs = rotinaOrigem.getStaticArgs()

	message = stargs["message"]

	rotinaOrigem.setIsEnabled(False)

	if "remind_text" in stargs:
		await message.author.send("<@{}> Estou lembrando para você de **{}**".format(message.author.id, stargs["remind_text"]))
	else:
		await message.author.send("<@{}> Estou te lembrando de algo!".format(message.author.id))