import asyncio
import time
import sys
import discord
import naviuteis

# @NOTE
# O cliente NaviClient irá ser o hospedeiro da biblioteca e receberá as chamadas dos eventos principais como on_message e on_ready.
# Quando isso ocorre, o cliente irá dispirar vários callback associados a este evento, ou seja, precisamos dizer ao NaviClient que queremos que ele
# notifique tais callback em certos eventos.

class NaviClient(discord.Client):
	def __init__(self, bot):
		"""Classe cliente responsável por comunicar com a API do discord.
		
		Args:
			bot (NaviBot): A instância do bot responsável.
		"""

		super().__init__()
		self._bot = bot

		self.remove_all()

	async def on_ready(self):
		for c in self._events["on_ready"]:
			if c.enabled:
				asyncio.get_running_loop().create_task(c.callback(self._bot))

	async def on_message(self, message):
		for c in self._events["on_message"]:
			if c.enabled:
				asyncio.get_running_loop().create_task(c.callback(self._bot, message))

	async def on_error(self, *args, **kwargs):
		for c in self._events["on_error"]:
			if c.enabled:
				asyncio.get_running_loop().create_task(c.callback(self._bot, sys.exc_info()))

	async def on_reaction_add(self, reaction, user):
		for c in self._events["on_reaction_add"]:
			if c.enabled:
				asyncio.get_running_loop().create_task(c.callback(self._bot, reaction, user))

	async def on_reaction_remove(self, reaction, user):
		for c in self._events["on_reaction_remove"]:
			if c.enabled:
				asyncio.get_running_loop().create_task(c.callback(self._bot, reaction, user))

	async def on_reaction_clear(self, message, reactions):
		for c in self._events["on_reaction_clear"]:
			if c.enabled:
				asyncio.get_running_loop().create_task(c.callback(self._bot, message, reactions))

	async def on_member_join(self, member):
		for c in self._events["on_member_join"]:
			if c.enabled:
				asyncio.get_running_loop().create_task(c.callback(self._bot, member))

	async def on_member_remove(self, member):
		for c in self._events["on_member_remove"]:
			if c.enabled:
				asyncio.get_running_loop().create_task(c.callback(self._bot, member))

	async def on_reload(self):
		await self.on_ready()

	def listen(self, event, callback, name=None):
		"""Atribui á um evento um novo callback a ser executado.
		
		Args:
			event (str): O nome do evento.
			callback (function): A coroutine a ser executada (encapsulada em um objeto NaviCallback)
			name (str, optional): O nome para tal callback, caso omitido, será utilizado o próprio nome da coroutine.
		"""

		for nc in self._events[event]:
			# Evita a sobreposição de callbacks.
			if name is None and (callback.__name__ == nc.name) or name == nc.name and callback == nc.callback:
				return
				
		self._events[event].append(NaviCallback(callback, name=name))

	def remove(self, event, callback, name=None):
		"""Remove de um evento um callback.
		
		Args:
			event (str): O nome do evento.
			callback (function): A corutine a ser removida.
			name (None, optional): Procurar por um nome específico atrelado ao callback.
		"""

		for nc in self._events[event]:
			if name is None and (callback.__name__ == nc.name and callback == nc.callback) or name == nc.name and callback == nc.callback:
				self._events[event].remove(nc)

	def remove_all_from(self, event):
		"""Remove todos os callbacks atribuidos a um evento.
		
		Args:
			event (str): O nome do evento.
		"""

		self._events[event] = []


	def remove_all(self):
		"""Remove todos os callbacks de todos os eventos.
		"""

		self._events = {
			"on_ready": [],
			"on_message": [],
			"on_error": [],
			"on_reaction_add": [],
			"on_reaction_remove": [],
			"on_reaction_clear": [],
			"on_member_join": [],
			"on_member_remove": []
		}

	def get_all_keys(self):
		"""Retorna o nome de todos os eventos disponíveis.
		
		Returns:
			list(str): Os nomes de eventos.
		"""

		return self._events.keys()

	def get_callbacks_from(self, event):
		"""Retorna uma lista de callbacks associados a um evento.
		
		Args:
			event (str): O nome do evento.
		
		Returns:
			list(NaviCallback): A lista de callbacks encapsuladas em objetos NaviCallback
		"""

		return self._events[event]

	def navi_start(self, token):
		"""Inicia o bot em modo sincrono e permanence executando o loop internamente.
		
		Args:
			token (str): O token de autenticação do bot.
		"""

		self.run(token)

	async def navi_stop(self):
		"""Pede assíncronamente a parada do bot em execução.
		"""

		await self.logout()

class NaviCallback:
	def __init__(self, callback, name=None):
		"""Objeto que representa uma função encapsulada.
		
		Args:
			callback (function): A função em questão, deverá ser uma coroutine.
			name (str, optional): Apelido dado para tal função.
		"""

		self.callback = callback
		self.name = callback.__name__ if name is None else name
		self.enabled = True
	
	def __str__(self):
		return f"{self.name}:{self.callback.__name__} enabled={self.enabled}"

class NaviRoutine(NaviCallback):
	def __init__(self, callback, timespan, name=None, waitfor=True, kwargs={}):
		"""Define uma rotina capaz de ser executada a cada intervalo de tempo.
		
		Args:
			callback (function): A função em questão, deverá ser uma coroutine.
			timespan (tuple(int, str)): Tuple cujo define uma quantidade em inteiro e uma string que define a unidade de tempo.
			name (str, optional): Apelido dado para tal função.
			waitfor (bool, optional): Define se deve Esperar até finalizar a execução da função.
			kwargs (dict, optional): Dicionário de argumentos passados diretamente para a função ao ser executada.
		"""

		super().__init__(callback, name)
		self.timespan = timespan
		self.running_task = None
		self.waitfor = waitfor
		self.kwargs = kwargs

		self._timespent = 0

	def get_timespent(self):
		"""Retorna em segundos o tempo gasto após a execução do callback.
		
		Returns:
			int: Um valor inteiro representando o tempo gasto de execução.
		"""

		return self._timespent

	def get_timespan_seconds(self):
		"""Retorna o número de segundos referente à este intervalo de tempo.
		
		Returns:
			int: O número de segundos.
		"""

		return naviuteis.timespan_to_seconds(self.timespan)

	async def run(self, bot):
		"""Executa o callback associado a rotina, dependendo dos atribudos, esperando o término da rotina ou não.
		
		Args:
			bot (NaviBot): O bot responsável pela execução da rotina atual.
		"""

		if not self.waitfor:
			asyncio.get_running_loop().create_task(self.callback(bot, self.kwargs))
			self._timespent = 0
		else:
			self._timespent = time.time()
			await self.callback(bot, self.kwargs)
			self._timespent = time.time() - self._timespent

	def __str__(self):
		return f"{self.name}:{self.callback.__name__} ({self.timespan[0]}, {self.timespan[1]}) waifor={self.waitfor} enabled={self.enabled} kwargs={self.kwargs}"

class NaviCommand(NaviCallback):
	def __init__(self, callback, name=None, owneronly=False, usage="", description="", permissions=[]):
		"""Define um objeto encapsulador de um comando do bot.
		
		Args:
			callback (function): A função em questão, deverá ser uma coroutine.
			name (str, optional): Apelido dado para tal função.
			owneronly (bool, optional): Define se apenas pode ser executado por owners.
			usage (str, optional): Informações de uso.
			description (str, optional): Descrição detalhada.
		"""
		super().__init__(callback, name)

		self.owneronly = owneronly
		self.usage = "Informações de uso não disponível" if not usage else usage
		self.description = "Nenhuma descrição disponível" if not description else description
		self.permissions = permissions

	async def run(self, bot, message, args, flags):
		"""Executa o callback associado a comando sem esperar pelo término.
		
		Args:
			bot (NaviBot): O bot responsável pela execução do comando atual.
			message (Message): A mensagem que originou este comando.
			args (list(str)): A lista de argumentos já separados.
			flags (dict): O dicionário de flags presentes.
		"""

		asyncio.get_running_loop().create_task(self.callback(bot, message, args, flags, self))
		