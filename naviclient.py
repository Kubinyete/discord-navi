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
			await c.callback(self._bot)

	async def on_message(self, message):
		for c in self._events["on_message"]:
			await c.callback(self._bot, message)

	async def on_error(self, *args, **kwargs):
		for c in self._events["on_error"]:
			await c.callback(self._bot, sys.exc_info())

	async def on_reaction_add(self, reaction, user):
		for c in self._events["on_reaction_add"]:
			await c.callback(self._bot, reaction, user)

	async def on_reaction_remove(self, reaction, user):
		for c in self._events["on_reaction_remove"]:
			await c.callback(self._bot, reaction, user)

	async def on_reaction_clear(self, message, reactions):
		for c in self._events["on_reaction_clear"]:
			await c.callback(self._bot, message, reactions)

	async def on_member_join(self, member):
		for c in self._events["on_member_join"]:
			await c.callback(self._bot, member)

	async def on_member_remove(self, member):
		for c in self._events["on_member_remove"]:
			await c.callback(self._bot, member)

	def listen(self, event, callback):
		try:
			self._events[event].append(NaviCallback(callback))
		except KeyError:
			pass

	def remove(self, event, callback):
		try:
			self._events[event].remove(callback)
		except KeyError:
			pass

	def remove_all_from(self, event):
		try:
			self._events[event] = []
		except KeyError:
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
	def __init__(self, callback, timespan, name=None):
		super().__init__(callback, name)
		self.timespan = timespan
		self.running_task = None

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

	async def run(self, bot, kwargs={}):
		self._timespent = time.time()
		await self.callback(bot, kwargs)
		self._timespent = time.time() - self._timespent

class NaviCommand(NaviCallback):
	def __init__(self, callback, name=None, owneronly=False, usage="", description=""):
		super().__init__(callback, name)

		self.owneronly = owneronly
		self.usage = "Informações de uso não disponíveis" if not usage else usage
		self.description = "Nenhuma descrição não disponível" if not description else description

	async def run(self, bot, message, args, flags, kwargs={}):
		await self.callback(bot, bot.naviClient, message, args, flags, kwargs)
		