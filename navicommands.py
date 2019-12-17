import asyncio
from naviclient import NaviCommand

class CommandDictionary:
	def __init__(self, bot):
		self._commands = {}
		self._bot = bot

	def load_from_module(self, module):
		for k in module.__dict__:
			if asyncio.iscoroutinefunction(module.__dict__[k]):
				if k.startswith("cli_"):
					self._commands[k[len("cli_"):]] = NaviCommand(module.__dict__[k], name=k[len("cli_"):], usage=self._bot.config.get("cli.commands.descriptions.{}.usage".format(k[len("cli_"):])))

				elif k.startswith("command_owner_"):
					self._commands[k[len("command_owner_"):]] = NaviCommand(module.__dict__[k], name=k[len("command_owner_"):], owneronly=True, usage=self._bot.config.get("commands.descriptions.{}.usage".format(k[len("command_owner_"):])), description=self._bot.config.get("commands.descriptions.{}.text".format(k[len("command_owner_"):])))

				elif k.startswith("command_"):
					self._commands[k[len("command_"):]] = NaviCommand(module.__dict__[k], name=k[len("command_"):], usage=self._bot.config.get("commands.descriptions.{}.usage".format(k[len("command_"):])), description=self._bot.config.get("commands.descriptions.{}.text".format(k[len("command_"):])))

	def get(self, key):
		try:
			return self._commands[key]
		except KeyError:
			return None

	def getCommands(self):
		return self._commands