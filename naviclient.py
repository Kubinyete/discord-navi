import asyncio
import time
import sys
import discord

# @NOTE
# O cliente NaviClient irá ser o hospedeiro da biblioteca e receberá as chamadas dos eventos principais como on_message e on_ready.
# Quando isso ocorre, o cliente irá dispirar vários callback associados a este evento, ou seja, precisamos dizer ao NaviClient que queremos que ele
# notifique tais callback em certos eventos.

class NaviClient(discord.Client):
	def __init__(self, bot):
		super().__init__()
		self._bot = bot

		self.remove_all()

	async def on_ready(self):
		for c in self._events["on_ready"]:
			asyncio.get_running_loop().create_task(c.callback(self._bot))

	async def on_message(self, message):
		for c in self._events["on_message"]:
			asyncio.get_running_loop().create_task(c.callback(self._bot, message))

	async def on_error(self, *args, **kwargs):
		for c in self._events["on_error"]:
			asyncio.get_running_loop().create_task(c.callback(self._bot, sys.exc_info()))

	async def on_reaction_add(self, reaction, user):
		for c in self._events["on_reaction_add"]:
			asyncio.get_running_loop().create_task(c.callback(self._bot, reaction, user))

	async def on_reaction_remove(self, reaction, user):
		for c in self._events["on_reaction_remove"]:
			asyncio.get_running_loop().create_task(c.callback(self._bot, reaction, user))

	async def on_reaction_clear(self, message, reactions):
		for c in self._events["on_reaction_clear"]:
			asyncio.get_running_loop().create_task(c.callback(self._bot, message, reactions))

	async def on_member_join(self, member):
		for c in self._events["on_member_join"]:
			asyncio.get_running_loop().create_task(c.callback(self._bot, member))

	async def on_member_remove(self, member):
		for c in self._events["on_member_remove"]:
			asyncio.get_running_loop().create_task(c.callback(self._bot, member))

	def listen(self, event, callback, name=None):
		try:
			for nc in self._events[event]:
				if name is None and (callback.__name__ == nc.name) or name == nc.name and callback == nc.callback:
					return
					
			self._events[event].append(NaviCallback(callback, name=name))
		except KeyError as e:
			self._bot.handle_exception(e)
			pass

	def remove(self, event, callback, name=None):
		try:
			for nc in self._events[event]:
				if name is None and (callback.__name__ == nc.name) or name == nc.name and callback == nc.callback:
					self._events[event].remove(nc)
		except KeyError as e:
			self._bot.handle_exception(e)
			pass

	def remove_all_from(self, event):
		try:
			self._events[event] = []
		except KeyError as e:
			self._bot.handle_exception(e)
			pass

	def remove_all(self):
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

	def navi_start(self, token):
		self.run(token)

	async def navi_stop(self):
		await self.logout()

class NaviCallback:
	def __init__(self, callback, name=None):
		self.callback = callback
		self.name = callback.__name__ if name is None else name
		self.enabled = True

class NaviRoutine(NaviCallback):
	def __init__(self, callback, timespan, name=None, waitfor=True, kwargs={}):
		super().__init__(callback, name)
		self.timespan = timespan
		self.running_task = None
		self.waitfor = waitfor
		self.kwargs = kwargs

		self._timespent = 0

	def get_timespent(self):
		return self._timespent

	@staticmethod
	def interval_to_seconds(timespan):
		segundos = 0

		value = timespan[0]
		unit = timespan[1]

		if unit == "s":
			segundos = value
		elif unit == "m":
			segundos = value * 60
		elif unit == "h":
			segundos = value * pow(60, 2)
		elif unit == "ms":
			segundos = value / 1000

		return segundos

	def get_timespan_seconds(self):
		return self.interval_to_seconds(self.timespan)

	async def run(self, bot):
		if not self.waitfor:
			asyncio.get_running_loop().create_task(self.callback(bot, self.kwargs))
			self._timespent = 0
		else:
			self._timespent = time.time()
			await self.callback(bot, self.kwargs)
			self._timespent = time.time() - self._timespent

class NaviCommand(NaviCallback):
	def __init__(self, callback, name=None, owneronly=False, usage="", description=""):
		super().__init__(callback, name)

		self.owneronly = owneronly
		self.usage = "Informações de uso não disponíveis" if not usage else usage
		self.description = "Nenhuma descrição disponível" if not description else description

	async def run(self, bot, message, args, flags):
		asyncio.get_running_loop().create_task(self.callback(bot, message, args, flags, self))
		