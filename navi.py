import asyncio
import os
import sys
import select
import discord
import enum
import re
import naviuteis
from navilog import LogManager
from navilog import LogType
from naviconfig import ConfigManager

class NaviEvent(enum.Enum):
	READY = 0		# on_ready
	MESSAGE = 1		# on_message

class NaviFeedback(enum.Enum):
	INFO = 0			# Mensagem de texto padrão
	ERROR = 1			# Aconteceu um erro com o comando
	SUCCESS = 2			# O comando foi bem sucedido
	WARNING = 3			# O comando foi bem sucedido porém é algo perigoso
	COMMAND_INFO = 4	# O comando não foi bem sucedido porém foi usado incorretamente

# @NOTE:
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
	# @NOTE: Deixando da forma que esta, com lista de rotinas associadas a um evento maior para poder ter controle durante a execução do Bot da remoção e adição destes modulos
	
	__eventosReady = []
	__eventosMessage = []

	async def on_ready(self):
		for e in self.__eventosReady:
			if e.obterAtivado():
				# @REWRITE
				#asyncio.get_running_loop().create_task(e.obterRotina()(self))
				asyncio.get_running_loop().create_task(e.executar(self, {"message": None}))
		

	async def on_message(self, message):
		for e in self.__eventosMessage:
			if e.obterAtivado():
				# @REWRITE
				#asyncio.get_running_loop().create_task(e.obterRotina()(self, message))
				asyncio.get_running_loop().create_task(e.executar(self, {"message": message}))

	def addRotinaEvento(self, evento, rotina):
		if evento == NaviEvent.READY:
			self.__eventosReady.append(rotina)
		elif evento == NaviEvent.MESSAGE:
			self.__eventosMessage.append(rotina)

class NaviRoutine:
	__every = None
	__unit = None

	def __init__(self, callback, name=None, every=None, unit=None, args={}, isPersistent=False):
		self.__enabled = True
		self.__isRunning = False
		self.__isPersistent = isPersistent
		self.__args = {"rotina_origem": self}

		self.setRotina(callback, name)
		self.setIntervalo(every, unit)
		self.atualizarArgs(args)


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
		return self.__args

	def obterAtivado(self):
		return self.__enabled

	def estaExecutando(self):
		return self.__isRunning

	def setExecutando(self, valor):
		self.__isRunning = valor

	def persistente(self):
		return self.__isPersistent

	def setPersistente(self, valor):
		self.__isPersistent = valor

	def ativar(self):
		self.__enabled = True

	def desativar(self):
		self.__enabled = False

	def atualizarArgs(self, updatedArgs):
		for k in updatedArgs.keys():
			self.__args[k] = updatedArgs[k]

	async def executar(self, clientOrigem, updatedArgs={}):
		#print("{} executando, callback={}, args={}, updatedArgs={}".format(self.obterNome(), self.obterNomeCallback(), self.obterArgs(), updatedArgs))

		self.atualizarArgs(updatedArgs)
		asyncio.get_running_loop().create_task(self.obterRotina()(clientOrigem, self.obterArgs()))

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

		self.__cliSelectedChannel = -1
		self.__cliSelectedChannelIsUser = False
		
		self.__naviClient = NaviClient()
		
		self.__commandHandlers = []
		self.__cliHandlers = []
		self.__tarefasAgendadas = {}

		self.__acoplarEventos()				# Pede para o cliente registrar os callbacks de cada evento
		self.__inicializarComandos()		# Prepara quais comandos estão disponíveis e seus callback para a callback principal de comandos callbackCommandHandler()
		self.__inicializarComandosCli()		# Prepara quais comandos estão disponíveis e seus callback para o callback da tarefa callbackCliListener()

	def __acoplarEventos(self):
		self.__naviClient.addRotinaEvento(NaviEvent.READY, NaviRoutine(self.callbackLog, isPersistent=True))
		self.__naviClient.addRotinaEvento(NaviEvent.READY, NaviRoutine(self.callbackActivity, isPersistent=True))
		self.__naviClient.addRotinaEvento(NaviEvent.READY, NaviRoutine(self.callbackCliListener, isPersistent=True))
		self.__naviClient.addRotinaEvento(NaviEvent.MESSAGE, NaviRoutine(self.callbackLog, isPersistent=True))
		self.__naviClient.addRotinaEvento(NaviEvent.MESSAGE, NaviRoutine(self.callbackCommandHandler, isPersistent=True))

	async def callbackLog(self, client, args):
		message = args["message"]

		if not message:
			self.__logManager.write("O bot foi iniciado com sucesso")
		else:
			self.__logManager.write(message, logtype=LogType.MESSAGE)

	async def callbackActivity(self, client, args):
		if not "loop" in args:
			asyncio.get_running_loop().create_task(self.__agendarTarefa(NaviRoutine(self.callbackActivity, name=None, every=self.__configManager.obter("global.bot_playing_delay"), unit="s", isPersistent=True), {"loop": True}))
			return

		activities = self.__configManager.obter("global.bot_playing")

		if activities != None:
			if self.__botPlayingIndex >= len(activities):
				self.__botPlayingIndex = 0

			await self.__naviClient.change_presence(activity=discord.Game(activities[self.__botPlayingIndex]))

			self.__botPlayingIndex = self.__botPlayingIndex + 1

	async def callbackCommandHandler(self, client, args):
		message = args["message"]

		# @NOTE: CommandHandler só aceita mensagens direcionadas ao bot
		if message.author == client.user or message.author.bot:
			return

		if message.content.startswith(self.__botPrefix):
			args, flags = naviuteis.listarArgumentos(message.content[len(self.__botPrefix):])

			if len(args) > 0:
				asyncio.get_running_loop().create_task(self.__interpretarComando(args, flags, client, message))

	async def callbackCliListener(self, client, args):
		if not "loop" in args.keys():
			asyncio.get_running_loop().create_task(self.__agendarTarefa(NaviRoutine(self.callbackCliListener, every=self.__configManager.obter("cli.update_delay"), unit="s", isPersistent=True), {"loop": True}))
			return

		clilines = []

		# @BUG:
		# Apenas funciona no Linux, ler da entrada padrão sem travar a thread principal é bem chato no Python e as funções principais ficam esperando ou newline ou EOF
		# Por enquanto a CLI só ficará disponível pelo Linux
		# 
		# Para entender o que está acontecendo:
		# Enquanto STDIN estiver disponível para leitura (tem algo no buffer), leia a linha presente (normalmente os terminais só enviam a linha quando o usuário aperta ENTER)
		while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
			#print("STDIN PERMITE LEITURA")
			clilines.append(re.sub(r"\n", r"", sys.stdin.readline()))

		for l in clilines:
			cliargs, cliflags = naviuteis.listarArgumentos(l)

			if len(cliargs) > 0:
				# @NOTE:
				# Usando await pois queremos que cada comando na cli seja sequencial
				await self.__interpretarComandoCli(client, cliargs, cliflags)

	async def callbackRemind(self, client, args):
		message = args["message"]
		rotinaOrigem = args["rotina_origem"]

		rotinaOrigem.desativar()

		if "remind_text" in rotinaOrigem.obterArgs().keys():
			await message.author.send("<@{}> Estou lembrando para você de **{}**".format(str(message.author.id), rotinaOrigem.obterArgs()["remind_text"]))
		else:
			await message.author.send("<@{}> Estou te lembrando de algo!")

	async def __agendarTarefa(self, rotina, args={}):
		segundos = 0
		unit = rotina.obterUnit()
		every = rotina.obterEvery()

		if unit == "s":
			segundos = segundos + every
		elif unit == "m":
			segundos = segundos + every * 60
		elif unit == "h":
			segundos = segundos + every * pow(60, 2)
		
		if segundos < 1:
			raise Exception("Unidade de tempo invalida, every={}, unit={}".format(every, unit))
		else:
			rotina.atualizarArgs(args)

			# Ja existe essa tarefa
			if rotina.obterNome() in self.__tarefasAgendadas.keys():
				# Se for outra com o mesmo nome, pare
				if not rotina is self.__obterTarefaAgendada(rotina.obterNome()):
					raise Exception("A tarefa a ser inserida nao pode substituir a atual")
				else:
					rotina.ativar()

					# É o mesmo objeto, verifique se já está em execução em outra coroutine
					if rotina.estaExecutando():
						# Ja esta executando em uma outra coroutine, apenas ative-a
						return

			# Caso seja o mesmo objeto, apenas vai atualizar a referência
			self.__tarefasAgendadas[rotina.obterNome()] = rotina

			while rotina.obterAtivado():
				rotina.setExecutando(True)

				await asyncio.sleep(segundos)

				if rotina.obterAtivado():
					asyncio.get_running_loop().create_task(rotina.executar(self.__naviClient))

			rotina.setExecutando(False)

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

	# @NOTE:
	# Para facilitar o uso do Bot e de manutenção de seus comandos, resolvi fazer um inicializador que já verifica quais métodos são comandos executáveis.
	# 
	# @TODO:
	# Os comandos deveriam ter uma forma de mostrar seu uso e descrição automáticamente ou de uma forma mais sofisticada, atualmente é feito manualmente pelo própria função do comando.
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
		self.__naviClient.run(self.__configManager.obter("global.bot_token"))

	# @SECTION: Funções auxiliares dos comandos
	
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

	# @SECTION: Manipuladores de cada comando (são automaticamente detectados ao iniciar com o prefixo 'command_')

	async def command_ping(self, h, args, flags, client, message):
		await message.channel.send("pong!")

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
			await self.send_feedback(message, NaviFeedback.COMMAND_INFO, text="Uso:\nsetgame [texto] [--clear]")
			return

		task = self.__obterTarefaAgendada(self.callbackActivity.__name__)
		
		if task == None:
			await self.send_feedback(message, NaviFeedback.ERROR)
			return
		
		if "clear" in flags:
			asyncio.get_running_loop().create_task(self.__agendarTarefa(task))
			await self.send_feedback(message, NaviFeedback.SUCCESS)
		else:
			task.desativar()

			try:
				await client.change_presence(activity=discord.Game(args[1]))
				await self.send_feedback(message, NaviFeedback.SUCCESS)
			except Exception:
				await self.send_feedback(message, NaviFeedback.ERROR)

	async def command_owner_send(self, h, args, flags, client, message):
		if len(args) < 3:
			await self.send_feedback(message, NaviFeedback.COMMAND_INFO, text="Uso:\nsend <channelid> <mensagem> [--user]")
			return
		
		try:
			c = None

			if not "user" in flags:
				c = client.get_channel(int(args[1]))
			else:
				c = client.get_user(int(args[1]))

			if c != None:
				try:
					await c.send(args[2])
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
				asyncio.get_running_loop().create_task(self.__agendarTarefa(tarefa))
		else:
			tarefa.desativar()

		await self.send_feedback(message, NaviFeedback.SUCCESS)

	async def command_remind(self, h, args, flags, client, message):
		if len(args) < 2 or not "time" in flags:
			await self.send_feedback(message, NaviFeedback.COMMAND_INFO, text="Uso:\nremind <nome_lembrete> [--time=[0-9]+(s|m|h)]")
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

		# @BUG:
		# Depois de executar o comando, o usuário fica sem poder fazer outro remind até a "thread" acabar, o que pode demorar o tempo que ele especificou x2, pois o "thread" está dormindo

		if tarefa == None:
			tarefa = NaviRoutine(self.callbackRemind, name=tarefa_str, every=every, unit=unit, args={"remind_text": args[1], "message": message})
			asyncio.get_running_loop().create_task(self.__agendarTarefa(tarefa))
			await self.send_feedback(message, NaviFeedback.SUCCESS)
		else:
			await self.send_feedback(message, NaviFeedback.ERROR, text="Recentemente já foi solicitado um remind, tente novamente mais tarde")

	async def command_embed(self, h, args, flags, client, message):
		if len(args) < 2 and (not "title" in flags and not "img" in flags):
			await self.send_feedback(message, NaviFeedback.COMMAND_INFO, text="Uso:\nembed [description] [--title=text] [--img=url]")
			return

		title = ""
		description = ""
		image = ""


		if len(args) > 1:
			description = args[1]

		if "title" in flags:
			title = flags["title"]

		if "img" in flags:
			image = flags["img"]


		embed = discord.Embed(title=title, description=description, color=discord.Colour.purple())
		embed.set_image(url=image)
		embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

		try:
			await message.channel.send(embed=embed)
			await self.send_feedback(message, NaviFeedback.SUCCESS)
		except Exception as e:
			await self.send_feedback(message, NaviFeedback.ERROR, exception=e)

	async def command_avatar(self, h, args, flags, client, message):
		if len(message.mentions) != 1:
			await self.send_feedback(message, NaviFeedback.COMMAND_INFO, text="Uso:\navatar <@Usuario>")
			return

		user = message.mentions[0]

		embed = discord.Embed(title="Avatar de {}".format(user.name), color=discord.Colour.purple())
		embed.set_image(url=user.avatar_url_as(size=256))
		embed.set_footer(text=user.name, icon_url=user.avatar_url_as(size=32))

		try:
			await message.channel.send(embed=embed)
			await self.send_feedback(message, NaviFeedback.SUCCESS)
		except Exception as e:
			await self.send_feedback(message, NaviFeedback.ERROR, exception=e)

	async def command_help(self, h, args, flags, client, message):
		helptext = "**Comandos disponíveis**\n\n"

		for h in self.__commandHandlers:
			helptext = helptext + "`{}`\n{}\n\n".format(h.obterAtivador(), self.__configManager.obter("commands.descriptions.{}".format(h.obterNomeCallback())))

		await self.send_feedback(message, NaviFeedback.SUCCESS, text=helptext)

	# @SECTION:
	# Comandos utilizados pela CLI oferecida pelo bot
	
	async def cli_echo(self, client, args, flags):
		self.__logManager.write(" ".join(args[1:]), logtype=LogType.DEBUG)
	
	async def cli_select(self, client, args, flags):
		if len(args) < 2 and not "show" in flags:
			self.__logManager.write("Uso:\nselect <channelid> [--user] [--show]", logtype=LogType.INFO)
			return

		if "show" in flags:
			self.__logManager.write("O canal selecionado é: {}, isuser={}".format(self.__cliSelectedChannel, self.__cliSelectedChannelIsUser), logtype=LogType.INFO)
			return

		try:
			self.__cliSelectedChannel = int(args[1])
		except Exception:
			self.__logManager.write("O id informado não é um número válido", logtype=LogType.INFO)
			return

		self.__cliSelectedChannelIsUser = "user" in flags

	async def cli_say(self, client, args, flags):
		if len(args) < 2:
			self.__logManager.write("Uso:\nsay <mensagem> [mensagem2...] [--user]", logtype=LogType.INFO)
			return

		try:
			c = None

			if not self.__cliSelectedChannelIsUser:
				c = client.get_channel(self.__cliSelectedChannel)
			else:
				c = client.get_user(self.__cliSelectedChannel)

			if c != None:
				try:
					await c.send(" ".join(args[1:]))
				except Exception as e:
					self.__logManager.write(str(e), LogType.ERROR)
			else:
				self.__logManager.write("O id do canal/usuário não foi encontrado (está esquecendo do --user?)", LogType.ERROR)
		except Exception as e:
			self.__logManager.write(str(e), LogType.ERROR)