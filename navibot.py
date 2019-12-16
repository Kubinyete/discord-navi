import discord
import asyncio
import aiohttp
import enum
import platform
import time
import sys
import tty
import termios
import importlib
import traceback
from naviclient import NaviClient
from naviclient import NaviEvent
from naviclient import NaviRoutine
from naviclient import NaviCommand
from navilog import LogManager
from navilog import LogType
from naviconfig import ConfigManager

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
	def __init__(self, configpath, cli=False):
		if type(configpath) != str:
			raise TypeError("'{}' não é uma str".fomat(configpath))

		# Componentes padrão
		self.logManager = LogManager("debug.log", self)
		self.configManager = ConfigManager(configpath, self.logManager)
		self.logManager.atualizarPath(self.configManager.obter("global.log_path"))

		# Componentes e flags do Loop de execução
		self.naviClient = None
		self.httpClientSession = None

		# Containers
		self.__tarefasAgendadas = {}

		# @NOTE
		# Só ativa o listener de CLI caso esteja no Linux
		self.cliEnabled = cli and platform.system() ==  "Linux"
		self.cliBuffer = ""
		self.cliContext = None

	def __acoplarEventos(self, navicallbacks):
		self.naviClient.addEventListener(NaviEvent.READY, NaviRoutine(self, navicallbacks.callbackLog, isPersistent=True))
		self.naviClient.addEventListener(NaviEvent.READY, NaviRoutine(self, navicallbacks.callbackActivity, isPersistent=True))
		self.naviClient.addEventListener(NaviEvent.READY, NaviRoutine(self, navicallbacks.callbackCliListener, isPersistent=True))
		self.naviClient.addEventListener(NaviEvent.MESSAGE, NaviRoutine(self, navicallbacks.callbackLog, isPersistent=True))
		self.naviClient.addEventListener(NaviEvent.MESSAGE, NaviRoutine(self, navicallbacks.callbackCommandHandler, isPersistent=True))

	def __acoplarComandos(self, mdl):
		for k in mdl.__dict__:
			if asyncio.iscoroutinefunction(mdl.__dict__[k]):
				if k.startswith("cli_"):
					self.__cliHandlers[k[len("cli_"):]] = NaviCommand(self, mdl.__dict__[k], name=k[len("cli_"):], usage=self.configManager.obter("cli.commands.descriptions.{}.usage".format(k[len("cli_"):])))
				elif k.startswith("command_owner_"):
					self.__commandHandlers[k[len("command_owner_"):]] = NaviCommand(self, mdl.__dict__[k], name=k[len("command_owner_"):], ownerOnly=True, usage=self.configManager.obter("commands.descriptions.{}.usage".format(k[len("command_owner_"):])), description=self.configManager.obter("commands.descriptions.{}.text".format(k[len("command_owner_"):])))
				elif k.startswith("command_"):
					self.__commandHandlers[k[len("command_"):]] = NaviCommand(self, mdl.__dict__[k], name=k[len("command_"):], usage=self.configManager.obter("commands.descriptions.{}.usage".format(k[len("command_"):])), description=self.configManager.obter("commands.descriptions.{}.text".format(k[len("command_"):])))

	def __acoplarScripts(self, mdl):
		# Externos
		for script in self.configManager.obter("commands.scripts"):
			self.__commandHandlers[script["command"]] = NaviCommand(self, mdl.__dict__["generic_runshell"], name=script["command"], ownerOnly=script["owner_only"], isEnabled=script["enabled"], staticArgs=script, usage=self.configManager.obter("commands.descriptions.{}.usage".format(script["command"])), description=self.configManager.obter("commands.descriptions.{}.text".format(script["command"])))

	def __desacoplarTodosEventos(self):
		self.naviClient.removeAllEventListener()

	def __handleException(self, e):
		self.logManager.write("{bold.red}An exception has ocurred while running, please check the stack trace for more info.{reset}")
		self.logManager.write("{{bold.red}}{}{{reset}} : {{bold.yellow}}{}{{reset}}".format(str(type(e)), e))
		self.logManager.write("{bold.yellow}\n" + traceback.format_exc() + "{reset}")

	async def __loopTarefa(self, rotina, futureRuntimeArgs):
		segundos = rotina.getIntervalInSeconds()

		timespent = 0

		while rotina.getIsEnabled():
			rotina.setIsRunning(True)

			await asyncio.sleep(segundos - timespent)

			if rotina.getIsEnabled():
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
	
	def __carregarModulo(self, modulo, canReload=True):
		if modulo in sys.modules:
			importlib.reload(sys.modules[modulo])
		else:
			try:
				importlib.import_module(modulo)
			except ImportError as e:
				self.__handleException(e)
				return

		return sys.modules[modulo]

	def inicializarModulos(self):
		self.__desacoplarTodosEventos()
		self.configManager.recarregarConfig()

		# Configurações de inicialização
		self.botPrefix = self.configManager.obter("global.bot_prefix")
		self.botPlayingIndex = 0
		
		# Containers
		self.__commandHandlers = {}
		self.__cliHandlers = {}

		self.__acoplarEventos(self.__carregarModulo("navicallbacks"))
		
		mdl = self.__carregarModulo("navicommands")
		self.__acoplarComandos(mdl)
		self.__acoplarScripts(mdl)

		for mdlstr in self.configManager.obter("global.bot_modules"):
			mdl = self.__carregarModulo(mdlstr)

			if mdl != None:
				self.__acoplarComandos(mdl)

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

	async def criarTarefaAsync(self, task, canWait=False):
		if canWait:
			await task
		else:
			asyncio.get_running_loop().create_task(task)

	async def interpretarComando(self, client, message, args, flags):
		# Existe esse comando em meu dicionário de comandos?
		h = self.obterComando(args[0])

		# Não existe, apenas cancele
		if h == None:
			return

		# O comando não irá executar de nenhuma maneira mesmo se não cair neste loop, NaviCommand.run() irá barrar, porém quero mostrar para o usuário que está explícitamente desativado
		if not h.getIsEnabled():
			await self.criarTarefaAsync(self.sendFeedback(message, NaviFeedback.WARNING, text="Este comando está atualmente desativado"))
		elif h.getOwnerOnly() and not self.isOwner(message.author):
			await self.criarTarefaAsync(self.sendFeedback(message, NaviFeedback.WARNING, text="Você não ter permissão para realizar esta ação"))
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
	
	async def fetchJson(self, url, params):
		async with self.httpClientSession.get(url, params=params) as resposta:
			return await resposta.json()


	async def agendarTarefa(self, rotina, futureRuntimeArgs={}):
		segundos = rotina.getIntervalInSeconds()
		
		if segundos < .033:
			self.logManager.write("A tarefa '{}' não pode ser inserida pois especifica um tempo de intervalo abaixo do mínimo permitido".format(rotina), logtype=LogType.ERROR)
		else:
			# Ja existe essa tarefa
			if rotina.getName() in self.__tarefasAgendadas.keys():
				# Escrever novamente a logica desta parte, pois queremos que aconteça o seguinte:
				# Caso já exista a tarefa, verifique se ela está rodanndo, caso não, substitua, se não, jogue uma Exception
				if rotina != self.__tarefasAgendadas[rotina.getName()] and self.__tarefasAgendadas[rotina.getName()].getIsRunning():
						# raise Exception("A tarefa '{}' a ser inserida não pode substituir a atual '{}' pos ainda está em execução".format(rotina, self.__tarefasAgendadas[rotina.getName()]))
						self.logManager.write("A tarefa '{}' a ser inserida não pode substituir a atual '{}' pos ainda está em execução".format(rotina, self.__tarefasAgendadas[rotina.getName()]), logtype=LogType.ERROR)
				else:
					rotina.setIsEnabled(True)

					# É o mesmo objeto, verifique se já está em execução em outra coroutine
					if rotina.getIsRunning():
						# Ja esta executando em uma outra coroutine, apenas ative-a
						return

			# Caso seja o mesmo objeto, apenas vai atualizar a referência
			# Caso contrário, irá inserir como uma nova
			self.__tarefasAgendadas[rotina.getName()] = rotina

			await self.criarTarefaAsync(self.__loopTarefa(rotina, futureRuntimeArgs))

	def isOwner(self, author):
		return author.id in self.configManager.obter("commands.owners")

	def rodar(self):
		# @NOTE
		# Congela a "thread" atual, deverá ser a ultima coisa a ser executada

		# @NOTE
		# naviClient(discord.Client) é quem vai gerenciar o loop do asyncio, não vamos mexer com isso por enquanto.
		self.naviClient = NaviClient()
		self.httpClientSession = aiohttp.ClientSession()

		# Pede para o cliente registrar os callbacks de cada evento
		# self.__acoplarEventos()

		# Prepara quais comandos estão disponíveis e seus callback para a callback principal de comandos callbackCommandHandler() e callbackCliListener()
		# self.__inicializarComandos()

		self.inicializarModulos()

		# CLI está ativada?
		if self.cliEnabled:
			self.cliStdinSavedAttr = termios.tcgetattr(sys.stdin)
			self.cliStdinCurrentAttr = termios.tcgetattr(sys.stdin)
			
			# Desativa o ECHO do console
			self.cliStdinCurrentAttr[3] = self.cliStdinCurrentAttr[3] & ~termios.ECHO
			
			# Desativa o modo CANONICAL do console
			self.cliStdinCurrentAttr[3] = self.cliStdinCurrentAttr[3] & ~termios.ICANON
			
			# Aplica as modificações
			termios.tcsetattr(sys.stdin, termios.TCSANOW, self.cliStdinCurrentAttr)

			# Ativa o modo de Input no LogManager
			self.logManager.setComportamentoCli(True)

		try:
			self.naviClient.rodar(self.configManager.obter("global.bot_token"))
		except Exception as e:
			self.logManager.write("{{bold.red}}{}{{reset}} : {{bold.yellow}}{}{{reset}}".format(type(e), e))
		finally:
			if self.cliEnabled:
				termios.tcsetattr(sys.stdin, termios.TCSANOW, self.cliStdinSavedAttr)

	async def fechar(self):
		# Pede para o cliente deslogar, fazendo com que a thread principal em NaviBot.rodar() volte do bloqueio
		self.logManager.setAtivado(False)
		self.logManager.fechar()

		await self.httpClientSession.close()
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
				text = "```\n{}```".format(text)
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
			self.__handleException(exception)