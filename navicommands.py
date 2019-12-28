import asyncio
from naviclient import NaviCommand

class CommandDictionary:
	def __init__(self, bot):
		self._commands = {}
		self._bot = bot

	def get(self, key):
		"""Retorna o comando de acordo com a chave informada.
		
		Args:
		    key (str): A chave que representa o comando.
		
		Returns:
		    NaviCommand, None: Retorna o comando associado a chave, caso não exista, retorna None.
		"""

		try:
			return self._commands[key]
		except KeyError:
			return None

	def set(self, key, handler):
		"""Atualiza a chave com um novo comando.
		
		Args:
		    key (str): A chave que representa o comando.
		    handler (NaviCommand): O novo comando.
		"""

		self._commands[key] = handler

	def get_commands(self):
		"""Retorna o objeto interno que detém todos os comandos.
		
		Returns:
		    dict: O dicionário de comandos.
		"""
		
		return self._commands