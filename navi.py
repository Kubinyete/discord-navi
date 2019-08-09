import asyncio
import os
import sys
import select
import discord
import enum
import re
import naviuteis
import time
import aiohttp
from navilog import LogManager
from navilog import LogType
from naviconfig import ConfigManager

class NaviEvent(enum.Enum):
	# on_ready
	READY = 0

	# on_message
	MESSAGE = 1

class NaviFeedback(enum.Enum):
	# Mensagem de texto padrão
	INFO = 0

	# Aconteceu um erro com o comando
	ERROR = 1

	# O comando foi bem sucedido
	SUCCESS = 2

	# O comando foi bem sucedido porém é algo perigoso
	WARNING = 3	

	# O comando não foi bem sucedido porém foi usado incorretamente
	COMMAND_INFO = 4

# @NOTE
# O cliente NaviClient irá ser o hospedeiro da biblioteca e receberá as chamadas dos eventos principais como on_message e on_ready.
# Quando isso ocorre, o cliente irá dispirar vários callback associados a este evento, ou seja, precisamos dizer ao NaviClient que queremos que ele
# notifique tais callback em certos eventos.
# 
# O NaviBot é o objeto principal que reune todas as partes separadas como o modulo de configurações e de log, inicializando eles e atribuindo
# ao cliente quais callbacks serão utilizadas.
# 
# Em teoria, o NaviClient ao receber em um evento, inicializa várias NaviRoutine (rotinas de execução) e cada rotina irá se responsabilizar por efetuar
# suas próprias coisas, como registrar log ou processar o comando.
# 
# Uma NaviRoutine pode portanto executar um NaviCommand (feito aqui com o callbackCommandHandler()) se o inicializador for válido.

class NaviClient(discord.Client):
	# @NOTE
	# Deixando da forma que esta, com lista de rotinas associadas a um evento maior para poder ter controle durante a execução do bot da remoção e adição destes modulos
	
	__eventosReady = []
	__eventosMessage = []

	async def on_ready(self):
		for e in self.__eventosReady:
			if e.obterAtivado():
				await e.executar(self, {"message": None})
		

	async def on_message(self, message):
		for e in self.__eventosMessage:
			if e.obterAtivado():
				await e.executar(self, {"message": message})

	def addRotinaEvento(self, evento, rotina):
		if evento == NaviEvent.READY:
			self.__eventosReady.append(rotina)
		elif evento == NaviEvent.MESSAGE:
			self.__eventosMessage.append(rotina)

	def rodar(self, token):
		self.run(token)

	async def fechar(self):
		await self.close()

class NaviRoutine:
	def __init__(self, callback, name=None, every=None, unit=None, staticArgs={}, isPersistent=False, canWait=False):
		self.__enabled = True
		self.__isRunning = False
		self.__isPersistent = isPersistent
		self.__canWait = canWait
		self.__staticArgs = staticArgs

		self.setRotina(callback, name)
		self.setIntervalo(every, unit)
		self.atualizarArgs(staticArgs)


	def obterRotina(self):
		return self.__callback

	def setRotina(self, callback, name=None):
		if not asyncio.iscoroutinefunction(callback):
			raise TypeError("O parâmetro callback deverá ser uma coroutine")

		self.__callback = callback

		if name != None:
			self.__name = name
		else:
			self.__name = self.__callback.__name__
	
	def obterNome(self):
		return self.__name

	def obterNomeCallback(self):
		return self.__callback.__name__

	def obterEvery(self):
		return self.__every

	def obterUnit(self):
		return self.__unit

	def setIntervalo(self, every, unit):
		if every != None and unit == None:
			raise Exception("O 'every' deverá também ser seguido do parametro 'unit' para especificar uma unidade")

		self.__every = every
		self.__unit = unit

	def obterArgs(self):
		return self.__staticArgs

	def obterAtivado(self):
		return self.__enabled

	def estaExecutando(self):
		return self.__isRunning

	def setExecutando(self, valor):
		self.__isRunning = valor

	def podeEsperarFinalizar(self):
		return self.__canWait

	def setEsperarFinalizar(self, valor):
		self.__canWait = valor

	def persistente(self):
		return self.__isPersistent

	def setPersistente(self, valor):
		self.__isPersistent = valor

	def ativar(self):
		self.__enabled = True

	def desativar(self):
		self.__enabled = False

	def atualizarArgs(self, newStaticArgs):
		for k in newStaticArgs.keys():
			self.__staticArgs[k] = newStaticArgs[k]

	async def executar(self, clientOrigem, runtimeArgs={}):
		if self.podeEsperarFinalizar():
			await self.obterRotina()(clientOrigem, self, runtimeArgs)
		else:
			asyncio.get_running_loop().create_task(self.obterRotina()(clientOrigem, self, runtimeArgs))

class NaviCommand:
	def __init__(self, callback, ativador=None, ownerOnly=False):
		self.setCallback(callback, ativador)
		self.__ownerOnly = ownerOnly

	def obterCallback(self):
		return self.__callback

	def setCallback(self, callback, ativador):
		if not asyncio.iscoroutinefunction(callback):
			raise TypeError("O parametro callback deverá ser uma coroutine")

		if ativador == None:
			if callback.__name__.startswith("command_"):
				self.__ativador = callback.__name__[len("command"):]
			else:
				self.__ativador = callback.__name__
		else:
			self.__ativador = ativador

		self.__callback = callback

	def obterNomeCallback(self):
		return self.__callback.__name__

	def obterAtivador(self):
		return self.__ativador

	def setAtivador(self, valor):
		self.__ativador = valor

	def obterOwnerOnly(self):
		return self.__ownerOnly

	def setOwnerOnly(valor):
		self.__ownerOnly = valor

	def obterAtivado(self):
		return self.__enabled

	def ativar(self):
		self.__enabled = True

	def desativar(self):
		self.__enabled = False

class NaviBot:
	def __init__(self, configpath):
		self.__logManager = LogManager("debug.log")
		self.__configManager = ConfigManager(configpath, self.__logManager)
		self.__logManager.atualizarPath(self.__configManager.obter("global.log_path"))

		self.__botPrefix = self.__configManager.obter("global.bot_prefix")
		self.__botPlayingIndex = 0

		self.__cliSelectedChannel = None
		
		self.__naviClient = NaviClient()
		self.__httpClientSession = aiohttp.ClientSession()
		
		# @TODO
		# Para melhorar o desempenho dos handlers, em vez de efetuarmos uma busca sequencial nessas duas listas, podemos utilizar
		# um dict com acesso direto
		self.__commandHandlers = []
		self.__cliHandlers = []

		self.__tarefasAgendadas = {}

		# Pede para o cliente registrar os callbacks de cada evento
		self.__acoplarEventos()

		# Prepara quais comandos estão disponíveis e seus callback para a callback principal de comandos callbackCommandHandler()
		self.__inicializarComandos()

		# Prepara quais comandos estão disponíveis e seus callback para o callback da tarefa callbackCliListener()
		self.__inicializarComandosCli()

	def __acoplarEventos(self):
		self.__naviClient.addRotinaEvento(NaviEvent.READY, NaviRoutine(self.callbackLog, isPersistent=True))
		self.__naviClient.addRotinaEvento(NaviEvent.READY, NaviRoutine(self.callbackActivity, isPersistent=True))
		
		# @NOTE
		# Se estiver com problemas em uma terminal windows, desative a rotina da CLI
		self.__naviClient.addRotinaEvento(NaviEvent.READY, NaviRoutine(self.callbackCliListener, isPersistent=True))

		self.__naviClient.addRotinaEvento(NaviEvent.MESSAGE, NaviRoutine(self.callbackLog, isPersistent=True))
		self.__naviClient.addRotinaEvento(NaviEvent.MESSAGE, NaviRoutine(self.callbackCommandHandler, isPersistent=True))

	async def __fetchJson(self, url, params):
		async with self.__httpClientSession.get(url, params=params) as resposta:
			return await resposta.json()

	async def callbackLog(self, client, rotinaOrigem, runtimeArgs):
		message = runtimeArgs["message"]

		if not message:
			self.__logManager.write("O bot foi iniciado com sucesso")
		else:
			self.__logManager.write(message, logtype=LogType.MESSAGE)

	async def callbackActivity(self, client, rotinaOrigem, runtimeArgs):
		if not "loop" in runtimeArgs:
			asyncio.get_running_loop().create_task(self.__agendarTarefa(NaviRoutine(self.callbackActivity, name=None, every=self.__configManager.obter("global.bot_playing_delay"), unit="s", isPersistent=True), {"loop": True}))
			return

		activities = self.__configManager.obter("global.bot_playing")

		if activities != None:
			if self.__botPlayingIndex >= len(activities):
				self.__botPlayingIndex = 0

			await self.__naviClient.change_presence(activity=discord.Game(activities[self.__botPlayingIndex]))

			self.__botPlayingIndex = self.__botPlayingIndex + 1

	async def callbackCommandHandler(self, client, rotinaOrigem, runtimeArgs):
		message = runtimeArgs["message"]

		# @NOTE
		# callbackCommandHandler() só aceita mensagens direcionadas ao bot e que não são diretamente de outro bot (pode causar um loop infinito)
		if message.author == client.user or message.author.bot:
			return

		if message.content.startswith(self.__botPrefix):
			args, flags = naviuteis.listarArgumentos(message.content[len(self.__botPrefix):])

			if len(args) > 0:
				asyncio.get_running_loop().create_task(self.__interpretarComando(args, flags, client, message))

	async def callbackCliListener(self, client, rotinaOrigem, runtimeArgs):
		if not "loop" in runtimeArgs.keys():
			asyncio.get_running_loop().create_task(self.__agendarTarefa(NaviRoutine(self.callbackCliListener, every=self.__configManager.obter("cli.update_delay"), unit="ms", isPersistent=True), {"loop": True}))
			return

		clilines = []

		# @BUG
		# Apenas funciona no Linux, ler da entrada padrão sem travar a thread principal é bem chato no Python e as funções principais ficam esperando ou newline ou EOF
		# Por enquanto a CLI só ficará disponível pelo Linux
		# 
		# Para entender o que está acontecendo:
		# Enquanto STDIN estiver disponível para leitura (tem algo no buffer), leia a linha presente (normalmente os terminais só enviam a linha quando o usuário aperta ENTER)
		while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
			clilines.append(re.sub(r"\n", r"", sys.stdin.readline()))

		for l in clilines:
			cliargs, cliflags = naviuteis.listarArgumentos(l)

			if len(cliargs) > 0:
				# @NOTE:
				# Usando await pois queremos que cada comando na CLI seja sequencial
				await self.__interpretarComandoCli(client, cliargs, cliflags)

	async def callbackRemind(self, client, rotinaOrigem, runtimeArgs):
		message = runtimeArgs["message"]

		rotinaOrigem.desativar()

		if "remind_text" in runtimeArgs:
			await message.author.send("<@{}> Estou lembrando para você de **{}**".format(str(message.author.id), runtimeArgs["remind_text"]))
		else:
			await message.author.send("<@{}> Estou te lembrando de algo!".format(str(message.author.id)))

	async def __agendarTarefa(self, rotina, futureRuntimeArgs={}):
		segundos = 0
		unit = rotina.obterUnit()
		every = rotina.obterEvery()

		if unit == "s":
			segundos = every
		elif unit == "m":
			segundos = every * 60
		elif unit == "h":
			segundos = every * pow(60, 2)
		elif unit == "ms":
			segundos = every / 1000
		
		if segundos < .100:
			# @NOTE
			# Tempo muito curto
			raise Exception("Unidade de tempo invalida, every={}, unit={}".format(every, unit))
		else:
			# Ja existe essa tarefa
			if rotina.obterNome() in self.__tarefasAgendadas.keys():
				# Se for outra com o mesmo nome, pare
				# @NOTE
				# Escrever novamente a logica desta parte, pois queremos que aconteça o seguinte:
				# Caso já exista a tarefa, verifique se ela está rodanndo, caso não, substitua, se não, jogue uma Exception
				if rotina != self.__tarefasAgendadas[rotina.obterNome()]:
					raise Exception("A tarefa a ser inserida nao pode substituir a atual")
				else:
					rotina.ativar()

					# É o mesmo objeto, verifique se já está em execução em outra coroutine
					if rotina.estaExecutando():
						# Ja esta executando em uma outra coroutine, apenas ative-a
						return

			# Caso seja o mesmo objeto, apenas vai atualizar a referência
			self.__tarefasAgendadas[rotina.obterNome()] = rotina

			timespent = 0

			while rotina.obterAtivado():
				rotina.setExecutando(True)

				await asyncio.sleep(segundos - timespent)

				if rotina.obterAtivado():
					# @TODO
					# Precisamos utilizar await nesta chamada abaixo, pois caso a tarefa acabe mas não dê tempo dela desativar sozinha seu estado de desativada,
					# esse loop continua e entra no sleep novamente, portanto devemos fazer cada chamada esperar o termino, e calculamos o tempo que perdemos nesta
					# execução e retiramos do sleep na proxima iteração (caso houver uma)
					# asyncio.get_running_loop().create_task(rotina.executar(self.__naviClient))
					
					timespent = time.time()

					await rotina.executar(self.__naviClient, futureRuntimeArgs)

					timespent = time.time() - timespent
					
					# self.__logManager.write("Ciclo da tarefa {}, timespent={:.3f}, segundos={}".format(rotina.obterNome(), timespent, segundos), logtype=LogType.DEBUG)
					
					if timespent >= segundos:
						# Perdemos um ou mais ciclos da tarefa, apenas notifique o log
						self.__logManager.write("Perdido um ciclo de execução da tarefa {}, timespent={:.3f}, segundos={}".format(rotina.obterNome(), timespent, segundos), logtype=LogType.WARNING)
						timespent = 0

			rotina.setExecutando(False)

			# Se esta rotina não for do sistema, não poderá ser ativada e desativada como quiser, portanto retire da estrutura
			if not rotina.persistente():
				self.__tarefasAgendadas.pop(rotina.obterNome())

	def __obterTarefaAgendada(self, nome):
		try:
			task = self.__tarefasAgendadas[nome]
		except KeyError:
			return None

		return task
		
	async def __interpretarComando(self, args, flags, client, message):
		for h in self.__commandHandlers:
			if args[0] == h.obterAtivador():
				if h.obterOwnerOnly() and not self.__isOwner(message.author):
					asyncio.get_running_loop().create_task(self.send_feedback(message, NaviFeedback.ERROR))
				else:
					asyncio.get_running_loop().create_task(h.obterCallback()(self, h, args, flags, client, message))

				return

	async def __interpretarComandoCli(self, client, cliargs, cliflags):
		for h in self.__cliHandlers:
			if cliargs[0] == h.obterAtivador():
				await h.obterCallback()(self, client, cliargs, cliflags)
				return

	# @NOTE
	# Para facilitar o uso do Bot e de manutenção de seus comandos, resolvi fazer um inicializador que já verifica quais métodos são comandos executáveis.
	def __inicializarComandos(self):
		for k in type(self).__dict__:
			if k.startswith("command_") and callable(type(self).__dict__[k]):
				if not k.startswith("command_owner_"):
					self.__commandHandlers.append(NaviCommand(type(self).__dict__[k], k[len("command_"):]))
				else:
					self.__commandHandlers.append(NaviCommand(type(self).__dict__[k], k[len("command_owner_"):], ownerOnly=True))

	def __inicializarComandosCli(self):
		for k in type(self).__dict__:
			if k.startswith("cli_") and callable(type(self).__dict__[k]):
				self.__cliHandlers.append(NaviCommand(type(self).__dict__[k], k[len("cli_"):]))

	def __isOwner(self, author):
		return author.id in self.__configManager.obter("commands.owners")

	def rodar(self):
		# @NOTE
		# Congela a "thread" atual, deverá ser a ultima coisa a ser executada
		self.__naviClient.rodar(self.__configManager.obter("global.bot_token"))

	async def fechar(self):
		await self.__naviClient.fechar()

	# @SECTION
	# Funções auxiliares dos comandos do bot
	
	async def send_feedback(self, message, feedback=NaviFeedback.SUCCESS, title=None, text=None, code=False, exception=None):
		if feedback == NaviFeedback.INFO:
			await message.add_reaction(r"ℹ")
		elif feedback == NaviFeedback.ERROR:
			await message.add_reaction(r"❌")
		elif feedback == NaviFeedback.SUCCESS:
			await message.add_reaction(r"✅")
		elif feedback == NaviFeedback.WARNING:
			await message.add_reaction(r"⚠")
		elif feedback == NaviFeedback.COMMAND_INFO:
			await message.add_reaction(r"ℹ")

		if text != None:
			embed = None

			if type(code) == str:
				text = "```{}\n{}```".format(code, text)
			elif code:
				text = "```{}```".format(text)
			else:
				if title != None:
					embed = discord.Embed(title=title, description=text, color=discord.Colour.purple())
				else:
					embed = discord.Embed(description=text, color=discord.Colour.purple())

				embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

			if embed != None:
				await message.channel.send(embed=embed)
			else:
				await message.channel.send(text)

		if exception != None:
			self.__logManager.write(str(exception), logtype=LogType.ERROR)

	# @SECTION
	# Manipuladores de cada comando (são automaticamente detectados ao iniciar com o prefixo 'command_' ou 'command_owner')

	async def command_ping(self, h, args, flags, client, message):
		await self.send_feedback(message, NaviFeedback.SUCCESS, text="pong!")

	async def command_remind(self, h, args, flags, client, message):
		if len(args) < 2 or not "time" in flags:
			await self.send_feedback(message, NaviFeedback.COMMAND_INFO, text="Uso:\nremind <nome_lembrete> [nome_lembrete2...] [--time=[0-9]+(s|m|h)]")
			return

		try:
			every = re.search("^[0-9]+", flags["time"])
			if every != None:
				every = int(every[0])
			unit = re.search("(h|m|s)$", flags["time"])
			if unit != None:
				unit = unit[0]
		except Exception as e:
			await self.send_feedback(message, NaviFeedback.ERROR, exception=e)
			return

		if every == None or unit == None:
			await self.send_feedback(message, NaviFeedback.ERROR, text="O argumento '--time' não está em um formato valido")
			return

		tarefa_str = "{}_{}".format(str(message.author.id), self.callbackRemind.__name__)
		tarefa = self.__obterTarefaAgendada(tarefa_str)

		if tarefa == None:
			tarefa = NaviRoutine(self.callbackRemind, name=tarefa_str, every=every, unit=unit, canWait=True)
			asyncio.get_running_loop().create_task(self.__agendarTarefa(tarefa, {"remind_text": " ".join(args[1:]), "message": message}))
			await self.send_feedback(message, NaviFeedback.SUCCESS)
		else:
			await self.send_feedback(message, NaviFeedback.ERROR, text="Recentemente já foi solicitado um 'remind', tente novamente mais tarde")

	async def command_embed(self, h, args, flags, client, message):
		if len(args) < 2 and (not "title" in flags and not "img" in flags):
			await self.send_feedback(message, NaviFeedback.COMMAND_INFO, text="Uso:\nembed [description] [description2...] [--title=text] [--img=url]")
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

		await self.send_feedback(message, NaviFeedback.SUCCESS)

	async def command_avatar(self, h, args, flags, client, message):
		if len(message.mentions) != 1:
			await self.send_feedback(message, NaviFeedback.COMMAND_INFO, text="Uso:\navatar <@Usuario>")
			return

		user = message.mentions[0]

		embed = discord.Embed(title="Avatar de {}".format(user.name), color=discord.Colour.purple())
		embed.set_image(url=user.avatar_url_as(size=256))
		embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

		await message.channel.send(embed=embed)
		await self.send_feedback(message, NaviFeedback.SUCCESS)

	async def command_osu(self, h, args, flags, client, message):
		if len(args) < 2:
			await self.send_feedback(message, NaviFeedback.COMMAND_INFO, text="Uso:\nosu <username> [--mode=std|taiko|ctb|mania]")
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
			json = await self.__fetchJson("https://" + self.__configManager.obter("external.osu.api_domain") + self.__configManager.obter("external.osu.api_getuser"), {"k": self.__configManager.obter("external.osu.api_key"), "u": " ".join(args[1:]), "mode": modeid, "type": "string"})

			if len(json) > 0:
				json = json[0]
			else:
				await self.send_feedback(message, NaviFeedback.ERROR, text="Não foi encontrado nenhum usuário com esse nome")
				return
		except Exception as e:
			await self.send_feedback(message, NaviFeedback.ERROR, exception=e)
			return

		description = """
**#{rank}** (:flag_{country}: **#{countryrank}**)

**Join date:**	{joindate}
**Playcount:**	{playcount}
**PP:**	{ppraw}
**Accuracy:**	{accuracy}

*View on* [osu.ppy.sh]({link})
""".format(rank=json["pp_rank"], country=json["country"].lower(), countryrank=json["pp_country_rank"], joindate=json["join_date"], playcount=json["playcount"], ppraw=json["pp_raw"], accuracy=json["accuracy"], link="https://" + self.__configManager.obter("external.osu.api_domain") + "/u/" + json["user_id"])

		embed = discord.Embed(title="Perfil de " + json["username"], description=description,color=discord.Colour.magenta())
		embed.set_thumbnail(url="https://" + self.__configManager.obter("external.osu.api_assets") + "/" + json["user_id"])
		embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

		await message.channel.send(embed=embed)
		await self.send_feedback(message, NaviFeedback.SUCCESS)

	async def command_help(self, h, args, flags, client, message):
		helptext = "**Comandos disponíveis**\n\n"

		for h in self.__commandHandlers:
			helptext = helptext + "`{}`\n{}\n\n".format(h.obterAtivador(), self.__configManager.obter("commands.descriptions.{}".format(h.obterNomeCallback())))

		await self.send_feedback(message, NaviFeedback.SUCCESS, text=helptext)

	async def command_owner_setprefix(self, h, args, flags, client, message):
		if len(args) < 2 and not "clear" in flags:
			await self.send_feedback(message, NaviFeedback.COMMAND_INFO, text="Uso:\nsetprefix [prefixo] [--clear]")
			return

		if "clear" in flags:
			self.__botPrefix = self.__configManager.obter("global.bot_prefix")
		else:
			self.__botPrefix = args[1]
		
		await self.send_feedback(message, NaviFeedback.SUCCESS)

	async def command_owner_setgame(self, h, args, flags, client, message):
		if len(args) < 2 and not "clear" in flags:
			await self.send_feedback(message, NaviFeedback.COMMAND_INFO, text="Uso:\nsetgame [texto] [texto2...] [--clear]")
			return

		task = self.__obterTarefaAgendada(self.callbackActivity.__name__)
		
		if task == None:
			await self.send_feedback(message, NaviFeedback.ERROR)
			return
		
		if "clear" in flags:
			asyncio.get_running_loop().create_task(self.__agendarTarefa(task, {"loop": True}))
			await self.send_feedback(message, NaviFeedback.SUCCESS)
		else:
			task.desativar()

			try:
				await client.change_presence(activity=discord.Game(" ".join(args[1:])))
				await self.send_feedback(message, NaviFeedback.SUCCESS)
			except Exception:
				await self.send_feedback(message, NaviFeedback.ERROR)

	async def command_owner_send(self, h, args, flags, client, message):
		if len(args) < 3:
			await self.send_feedback(message, NaviFeedback.COMMAND_INFO, text="Uso:\nsend <channelid> <mensagem> [mensagem2...] [--user]")
			return
		
		try:
			c = None

			if not "user" in flags:
				c = client.get_channel(int(args[1]))
			else:
				c = client.get_user(int(args[1]))

			if c != None:
				try:
					await c.send(" ".join(args[2:]))
					await self.send_feedback(message, NaviFeedback.SUCCESS)
				except Exception as e:
					await self.send_feedback(message, NaviFeedback.ERROR, exception=e)
			else:
				await self.send_feedback(message, NaviFeedback.ERROR, text="O id do canal/usuário não foi encontrado (está esquecendo do --user?)")
		except Exception as e:
			await self.send_feedback(message, NaviFeedback.ERROR, exception=e)

	async def command_owner_argtester(self, h, args, flags, client, message):
		await self.send_feedback(message, NaviFeedback.SUCCESS, text="handler={}\nativador={}\nargs={}\nflags={}".format(h.obterNomeCallback(), h.obterAtivador(), str(args), str(flags)))

	async def command_owner_task(self, h, args, flags, client, message):
		if len(args) < 2 or (not "enable" in flags and not "disable" in flags):
			if "showall" in flags:
				str = ""
				for k in self.__tarefasAgendadas.keys():
					str = str + "**{}**\n`callback={}, every={}, unit={}, enabled={}, isrunning={}, ispersistent={}`\n\n".format(k, self.__tarefasAgendadas[k].obterNomeCallback(), self.__tarefasAgendadas[k].obterEvery(), self.__tarefasAgendadas[k].obterUnit(), self.__tarefasAgendadas[k].obterAtivado(), self.__tarefasAgendadas[k].estaExecutando(), self.__tarefasAgendadas[k].persistente())

				await self.send_feedback(message, NaviFeedback.SUCCESS, text=str)
				return
				
			await self.send_feedback(message, NaviFeedback.COMMAND_INFO, text="Uso:\ntask [nome_tarefa] [--showall] [--enable] [--disable]")
			return

		tarefa = None

		try:
			tarefa = self.__tarefasAgendadas[args[1]]
		except Exception:
			await self.send_feedback(message, NaviFeedback.ERROR, text="A tarefa não foi encontrada")
			return

		if "enable" in flags:
			if not tarefa.obterAtivado():
				asyncio.get_running_loop().create_task(self.__agendarTarefa(tarefa, {"loop": True}))
		else:
			tarefa.desativar()

		await self.send_feedback(message, NaviFeedback.SUCCESS)

	# @SECTION
	# Comandos disponibilizados para a CLI oferecida pelo bot
	
	async def cli_echo(self, client, args, flags):
		self.__logManager.write(" ".join(args[1:]), logtype=LogType.DEBUG)
	
	async def cli_select(self, client, args, flags):
		if len(args) < 2 and not "show" in flags:
			self.__logManager.write("Uso:\nselect <channelid> [--user] [--show]", logtype=LogType.INFO)
			return

		if "show" in flags:
			if self.__cliSelectedChannel == None:
				self.__logManager.write("Nenhum canal/usuário está selecionado", logtype=LogType.INFO)
			elif type(self.__cliSelectedChannel) == discord.User:
				self.__logManager.write("O usuário selecionado é: {} ({})".format(self.__cliSelectedChannel.name, self.__cliSelectedChannel.id), logtype=LogType.INFO)
			elif type(self.__cliSelectedChannel) == discord.TextChannel:
				self.__logManager.write("O canal selecionado é: {}#{} ({})".format(self.__cliSelectedChannel.guild.name, self.__cliSelectedChannel.name, self.__cliSelectedChannel.id), logtype=LogType.INFO)
			else:
				self.__logManager.write("O canal selecionado é: {}".format(str(self.__cliSelectedChannel)), logtype=LogType.INFO)

			return

		try:
			cid = int(args[1])
		except Exception:
			self.__logManager.write("O id informado não é um número", logtype=LogType.ERROR)
			return

		if "user" in flags:
			self.__cliSelectedChannel = client.get_user(cid)
		else:
			self.__cliSelectedChannel = client.get_channel(cid)

		if self.__cliSelectedChannel == None or (type(self.__cliSelectedChannel) != discord.TextChannel and type(self.__cliSelectedChannel) != discord.User):
			self.__logManager.write("O id informado não é um canal/usuário válido", logtype=LogType.ERROR)
		else:
			await self.cli_select(client, {}, {"show": True})

	async def cli_say(self, client, args, flags):
		if len(args) < 2:
			self.__logManager.write("Uso:\nsay <mensagem> [mensagem2...]", logtype=LogType.INFO)
			return

		if self.__cliSelectedChannel == None:
			self.__logManager.write("Nenhum canal foi selecionado para enviar a mensagem, selecione utilizando o comando 'select'", logtype=LogType.INFO)
			return

		try:
			await self.__cliSelectedChannel.send(" ".join(args[1:]))
		except Exception as e:
			self.__logManager.write(str(e), LogType.ERROR)

	async def cli_quit(self, client, args, flags):
		self.__logManager.write("Desligando o cliente...", logtype=LogType.WARNING)
		self.__logManager.desativar()
		self.__logManager.fechar()
		await self.__httpClientSession.close()
		await self.fechar()
