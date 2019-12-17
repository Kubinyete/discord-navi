import asyncio
from naviclient import NaviCommand

class CommandDictionary:
	def __init__(self, bot):
		self._commands = {}
		self._bot = bot

	def get(self, key):
		try:
			return self._commands[key]
		except KeyError:
			return None

	def set(self, key, handler):
		self._commands[key] = handler

	def getCommands(self):
		return self._commands