import discord
import asyncio
import aiohttp
import enum
import platform
import time
from naviclient import NaviClient
from naviclient import NaviEvent
from naviclient import NaviRoutine
from naviclient import NaviCommand
from navilog import LogManager
from navilog import LogType
from naviconfig import ConfigManager
import navicallbacks
import navicommands

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

class NaviBot:
	def __init__(self, configpath):
		if type(configpath) != str:
			raise TypeError("'{}' não é uma str".fomat(configpath))

		# Componentes
		self.logManager = LogManager("debug.log")
		self.configManager = ConfigManager(configpath, self.logManager)
		self.logManager.atualizarPath(self.configManager.obter("global.log_path"))

		self.naviClient = NaviClient()
		self.httpClientSession = aiohttp.ClientSession()

		# Configurações de inicialização
		self.botPrefix = self.configManager.obter("global.bot_prefix")
		self.botPlayingIndex = 0

		self.cliSelectedChannel = None

		self.__commandHandlers = {}
		self.__cliHandlers = {}
		self.__tarefasAgendadas = {}
		
		# Pede para o cliente registrar os callbacks de cada evento
		self.__acoplarEventos()
		# Prepara quais comandos estão disponíveis e seus callback para a callback principal de comandos callbackCommandHandler() e callbackCliListener()
		self.__inicializarComandos()

	def __acoplarEventos(self):
		self.naviClient.addEventListener(NaviEvent.READY, NaviRoutine(self, navicallbacks.callbackLog, isPersistent=True))
		self.naviClient.addEventListener(NaviEvent.READY, NaviRoutine(self, navicallbacks.callbackActivity, isPersistent=True))
		
		# @NOTE
		# Só ativa o listener de CLI caso esteja no Linux
		if platform.system() ==  "Linux":
			self.naviClient.addEventListener(NaviEvent.READY, NaviRoutine(self, navicallbacks.callbackCliListener, isPersistent=True))
		else:
			self.logManager.write("Rodando em um sistema não Linux, desativando evento da CLI", logtype=LogType.WARNING)

		self.naviClient.addEventListener(NaviEvent.MESSAGE, NaviRoutine(self, navicallbacks.callbackLog, isPersistent=True))
		self.naviClient.addEventListener(NaviEvent.MESSAGE, NaviRoutine(self, navicallbacks.callbackCommandHandler, isPersistent=True))

	async def fetchJson(self, url, params):
		async with self.httpClientSession.get(url, params=params) as resposta:
			return await resposta.json()

	async def agendarTarefa(self, rotina, futureRuntimeArgs={}):
		segundos = rotina.getIntervalInSeconds()
		
		if segundos < .100:
			raise Exception("Tempo mínimo atingido, 'segundos' = {}".format(segundos))
		else:
			# Ja existe essa tarefa
			if rotina.getName() in self.__tarefasAgendadas.keys():
				# Se for outra com o mesmo nome, pare
				# @NOTE
				# Escrever novamente a logica desta parte, pois queremos que aconteça o seguinte:
				# Caso já exista a tarefa, verifique se ela está rodanndo, caso não, substitua, se não, jogue uma Exception
				if rotina != self.__tarefasAgendadas[rotina.getName()]:
					raise Exception("A tarefa '{}' a ser inserida não pode substituir a atual '{}'".format(rotina, self.__tarefasAgendadas[rotina.getName()]))
				else:
					rotina.setIsEnabled(True)

					# É o mesmo objeto, verifique se já está em execução em outra coroutine
					if rotina.getIsRunning():
						# Ja esta executando em uma outra coroutine, apenas ative-a
						return

			# Caso seja o mesmo objeto, apenas vai atualizar a referência
			# Caso contrário, irá inserir como uma nova
			self.__tarefasAgendadas[rotina.getName()] = rotina

			timespent = 0

			while rotina.getIsEnabled():
				rotina.setIsRunning(True)

				await asyncio.sleep(segundos - timespent)

				if rotina.getIsEnabled():
					# @TODO
					# Precisamos utilizar await nesta chamada abaixo, pois caso a tarefa acabe mas não dê tempo dela desativar sozinha seu estado de desativada,
					# esse loop continua e entra no sleep novamente, portanto devemos fazer cada chamada esperar o termino, e calculamos o tempo que perdemos nesta
					# execução e retiramos do sleep na proxima iteração (caso houver uma)
					# asyncio.get_running_loop().create_task(rotina.executar(self.naviClient))
					
					timespent = time.time()
					await rotina.run(self.naviClient, futureRuntimeArgs)
					timespent = time.time() - timespent
					
					if timespent >= segundos:
						# Perdemos um ou mais ciclos da tarefa, apenas notifique o log
						self.logManager.write("Perdido um ciclo de execução da tarefa '{}', timespent = '{:.3f}', segundos= '{}'".format(rotina.obterNome(), timespent, segundos), logtype=LogType.WARNING)
						timespent = 0

			rotina.setIsRunning(False)

			# Se esta rotina não for do sistema, não poderá ser ativada e desativada como quiser, portanto retire da estrutura
			if not rotina.getIsPersistent():
				self.__tarefasAgendadas.pop(rotina.getName())

	def obterTarefaAgendada(self, nome):
		if not nome in self.__tarefasAgendadas:
			return None
		
		return self.__tarefasAgendadas[nome]

	def obterTarefasAgendadas(self):
		ret = []

		for k in self.__tarefasAgendadas:
			ret.append(self.__tarefasAgendadas[k])
		
		return ret

	def obterCommandHandlers(self):
		ret = []

		for k in self.__commandHandlers:
			ret.append(self.__commandHandlers[k])
		
		return ret

	def obterCliHandlers(self):
		ret = []

		for k in self.__cliHandlers:
			ret.append(self.__cliHandlers[k])
		
		return ret
		
	def obterComando(self, nome):
		if not nome in self.__commandHandlers:
			return None

		return self.__commandHandlers[nome]

	def obterComandoCli(self, nome):
		if not nome in self.__cliHandlers:
			return None

		return self.__cliHandlers[nome]

	async def interpretarComando(self, client, message, args, flags):
		# Existe esse comando em meu dicionário de comandos?
		h = self.obterComando(args[0])

		# Não existe, apenas cancele
		if h == None:
			return

		# O comando não irá executar de nenhuma maneira mesmo se não cair neste loop, NaviCommand.run() irá barrar, porém quero mostrar para o usuário que está explícitamente desativado
		if not h.getIsEnabled():
			asyncio.get_running_loop().create_task(self.sendFeedback(message, NaviFeedback.WARNING, text="Este comando está atualmente desativado"))
		elif h.getOwnerOnly() and not self.isOwner(message.author):
			asyncio.get_running_loop().create_task(self.sendFeedback(message, NaviFeedback.WARNING, text="Você não ter permissão para realizar esta ação"))
		else:
			await h.run(client, message, args, flags)

	async def interpretarComandoCli(self, client, cliargs, cliflags):
		# Existe esse comando em meu dicionário de comandos?
		h = self.obterComandoCli(cliargs[0])

		# Não existe, apenas cancele
		if h == None:
			return

		# Na CLI não temos uma message, passe None
		await h.run(client, None, cliargs, cliflags)
		
	# @NOTE
	# Para facilitar o uso do Bot e de manutenção de seus comandos, resolvi fazer um inicializador que já verifica quais métodos são comandos executáveis.
	def __inicializarComandos(self):
		# Nativos
		for k in navicommands.__dict__:
			if asyncio.iscoroutinefunction(navicommands.__dict__[k]):
				if k.startswith("cli_"):
					self.__cliHandlers[k[len("cli_"):]] = NaviCommand(self, navicommands.__dict__[k], name=k[len("cli_"):], usage=self.configManager.obter("cli.commands.descriptions.{}.usage".format(k[len("cli_"):])))
				elif k.startswith("command_owner_"):
					self.__commandHandlers[k[len("command_owner_"):]] = NaviCommand(self, navicommands.__dict__[k], name=k[len("command_owner_"):], ownerOnly=True, usage=self.configManager.obter("commands.descriptions.{}.usage".format(k[len("command_owner_"):])), description=self.configManager.obter("commands.descriptions.{}.text".format(k[len("command_owner_"):])))
				elif k.startswith("command_"):
					self.__commandHandlers[k[len("command_"):]] = NaviCommand(self, navicommands.__dict__[k], name=k[len("command_"):], usage=self.configManager.obter("commands.descriptions.{}.usage".format(k[len("command_"):])), description=self.configManager.obter("commands.descriptions.{}.text".format(k[len("command_"):])))

		# Externos
		for script in self.configManager.obter("commands.scripts"):
			self.__commandHandlers[script["command"]] = NaviCommand(self, navicommands.__dict__["generic_runshell"], name=script["command"], ownerOnly=script["owner_only"], isEnabled=script["enabled"], staticArgs=script, usage=self.configManager.obter("commands.descriptions.{}.usage".format(script["command"])), description=self.configManager.obter("commands.descriptions.{}.text".format(script["command"])))

	def isOwner(self, author):
		return author.id in self.configManager.obter("commands.owners")

	def rodar(self):
		# @NOTE
		# Congela a "thread" atual, deverá ser a ultima coisa a ser executada
		self.naviClient.rodar(self.configManager.obter("global.bot_token"))

	async def fechar(self):
		await self.naviClient.fechar()

	# @SECTION
	# Funções auxiliares dos comandos do bot
	
	async def sendFeedback(self, message, feedback=NaviFeedback.SUCCESS, title=None, text=None, code=False, exception=None):
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
			self.logManager.write(str(exception), logtype=LogType.ERROR)