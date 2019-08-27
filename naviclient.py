import discord
import asyncio
import enum
import navibot

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
			if e.getIsEnabled():
				await e.run(self, {"message": None})
		

	async def on_message(self, message):
		for e in self.__eventosMessage:
			if e.getIsEnabled():
				await e.run(self, {"message": message})

	def addEventListener(self, evento, rotina):
		if evento == NaviEvent.READY:
			self.__eventosReady.append(rotina)
		elif evento == NaviEvent.MESSAGE:
			self.__eventosMessage.append(rotina)

	def rodar(self, token):
		self.run(token)

	async def fechar(self):
		# Vai deslogar sem desativar o loop de execução, fazendo com que rodar() pare
		await self.logout()

class NaviEvent(enum.Enum):
	# on_ready
	READY = 0
	# on_message
	MESSAGE = 1

class NaviCallback:
	def __init__(self, navibot, callback, customName, staticArgs, canWait, isEnabled):
		self.setNaviBot(navibot)
		self.setCallback(callback)
		self.setName(customName)
		self.setStaticArgs(staticArgs)
		self.setCanWait(canWait)
		self.setIsEnabled(isEnabled)

	def getNaviBot(self):
		return self.__naviBot

	def setNaviBot(self, bot):
		if type(bot) != navibot.NaviBot:
			raise TypeError("'{}' não é um objeto do tipo NaviBot".format(bot))

		self.__naviBot = bot

	def getCallback(self):
		return self.__callback

	def setCallback(self, callback):
		if not asyncio.iscoroutinefunction(callback):
			raise TypeError("'{}' não é uma callback do tipo coroutine".format(callback))

		self.__callback = callback

	def getName(self):
		return self.__name

	def setName(self, customName):
		if customName == None:
			self.__name = self.__callback.__name__
		else:
			self.__name = customName

	def setStaticArgs(self, staticArgs):
		if type(staticArgs) != dict:
			raise TypeError("'{}' não é um dicionário".format(staticArgs))

		self.__staticArgs = staticArgs

	def getStaticArgs(self):
		return self.__staticArgs

	def setCanWait(self, state):
		if type(state) != bool:
			raise TypeError("'{}' não é um bool".format(state))

		self.__canWait = state

	def getCanWait(self):
		return self.__canWait

	def setIsEnabled(self, state):
		if type(state) != bool:
			raise TypeError("'{}' não é um bool".format(state))

		self.__enabled = state

	def getIsEnabled(self):
		return self.__enabled


class NaviRoutine(NaviCallback):
	def __init__(self, navibot, callback, name=None, every=None, unit=None, staticArgs={}, isPersistent=False, canWait=False, isEnabled=True):
		super().__init__(navibot, callback, name, staticArgs, canWait, isEnabled)
		self.setInterval(every, unit)
		self.setIsPersistent(isPersistent)
		self.setIsRunning(False)

	def setInterval(self, every, unit):
		if every != None:
			if (type(every) == int or type(every) == float) and unit in ["h", "m", "s", "ms"]:
				self.__every = every
				self.__unit = unit
			else:
				raise TypeError("O formato de 'every' ({})  e 'unit' ({}) está incorreto".format(every, unit))

	def getIntervalInSeconds(self):
		segundos = 0

		if self.__unit == "s":
			segundos = self.__every
		elif self.__unit == "m":
			segundos = self.__every * 60
		elif self.__unit == "h":
			segundos = self.__every * pow(60, 2)
		elif self.__unit == "ms":
			segundos = self.__every / 1000

		return segundos

	def getInterval(self):
		return (self.__every, self.__unit)

	def getIsScheduled(self):
		return self.__every != None and self.__unit != None

	def setIsRunning(self, state):
		if type(state) != bool:
			raise TypeError("'{}' não é um bool".format(state))

		self.__isRunning = state

	def getIsRunning(self):
		return self.__isRunning

	def setIsPersistent(self, state):
		if type(state) != bool:
			raise TypeError("'{}' não é um bool".format(state))

		self.__isPersistent = state

	def getIsPersistent(self):
		return self.__isPersistent

	async def run(self, client, runtimeArgs):
		if self.getIsEnabled():
			# @NOTE
			# Como na inicialização do NaviBot nós referenciamos os callback através do self, ele já está embutido na hora de chamar o callback
			# @TODO
			# Desacoplar esses callbacks da instancia do self e apenas receberem e comunicarem pelo bot enviado por argumento
			if self.getCanWait():
				await self.getCallback()(self.getNaviBot(), client, self, runtimeArgs)
			else:
				asyncio.get_running_loop().create_task(self.getCallback()(self.getNaviBot(), client, self, runtimeArgs))

			return True

		return False

class NaviCommand(NaviCallback):
	def __init__(self, navibot, callback, name=None, staticArgs={}, ownerOnly=False, canWait=False, usage="", description="", isEnabled=True):
		super().__init__(navibot, callback, name, staticArgs, canWait, isEnabled)
		self.setOwnerOnly(ownerOnly)
		self.setUsage(usage)
		self.setDescription(description)

	def getOwnerOnly(self):
		return self.__ownerOnly

	def setOwnerOnly(self, state):
		if type(state) != bool:
			raise TypeError("'{}' não é um bool".format(state))

		self.__ownerOnly = state

	def getUsage(self):
		return self.__usage

	def setUsage(self, string):
		if type(string) != str:
			raise TypeError("'{}' não é um str".format(string))

		self.__usage = string

	def getDescription(self):
		return self.__description

	def setDescription(self, string):
		if type(string) != str:
			raise TypeError("'{}' não é um str".format(string))

		self.__description = string

	async def run(self, client, message, args, flags):
		if self.getIsEnabled():
			if self.getCanWait():
				await self.getCallback()(self.getNaviBot(), self, client, message, args, flags)
			else:
				asyncio.get_running_loop().create_task(self.getCallback()(self.getNaviBot(), self, client, message, args, flags))

			return True

		return False