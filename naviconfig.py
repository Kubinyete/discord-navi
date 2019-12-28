import navilog
import json

class ConfigManager:
	def __init__(self, path, bot):
		"""Componente responsável por carregar, armazenar e alterar as informações do arquivo de configurações.
		
		Args:
		    path (str): O caminho do arquivo de configurações JSON a ser utilizado.
		    bot (TYPE): A instância do bot responsável.
		"""
		
		self._bot = bot
		self.path = path
		self.load()

	def load(self):
		"""Preenche o dicionário de chaves de acordo com o arquivo de configurações informado.
		"""

		self._keys = {}
		
		try:
			with open(self.path, "r", encoding="utf-8") as f:
				self._keys = json.loads("".join(f.readlines()))
				f.close()
		except IOError:
			self._bot.log.write(f"Não foi possível carregar o arquivo de configurações '{self.path}'", logtype=navilog.ERROR)
		except ValueError:
			self._bot.log.write(f"Não foi possível converter o arquivo de configurações '{self.path}' em um objeto JSON", logtype=navilog.ERROR)

	def get(self, indice):
		"""Obtém uma chave de configuração.
		
		Args:
		    indice (str): O caminho que representa a chave de configuração, de forma separada por pontos: chavepai.chavefilho.meuvalor
		
		Returns:
		    Any: O tipo desejado encontrado pela chave, caso falhe, retornará uma string vazia equivalente à "".
		"""

		chaves = indice.split(".")
		atual = self._keys

		if len(chaves) <= 0:
			return
			
		try:
			for i in chaves:
				atual = atual[i]
		except KeyError:
			self._bot.log.write(f"Não foi possível encontrar a chave de configurações '{indice}'", logtype=navilog.WARNING)
			return ""

		return atual

	def set(self, indice, val):
		"""Atualiza o valor de uma chave.
		
		Args:
		    indice (str): O caminho que representa a chave de configuração.
		    val (Any): O valor a ser atribuido.
		"""

		chaves = indice.split(".")
		atual = self._keys

		if len(chaves) <= 0:
			return

		try:
			for i in chaves[:-1]:
				atual = atual[i]

			atual[i] = val
		except KeyError:
			self._bot.log.write(f"Não foi possível atribuir na chave de configurações '{indice}'", logtype=navilog.WARNING)
			