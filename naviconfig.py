import navilog
import json

class ConfigManager:
	def __init__(self, path, bot):
		self._bot = bot
		self.path = path
		self.load()

	def load(self):
		self._keys = {}
		
		try:
			with open(self.path, "r", encoding="utf-8") as f:
				self._keys = json.loads("".join(f.readlines()))
				f.close()
		except IOError:
			self._bot.log.write("Não foi possível carregar o arquivo de configurações (" + self.path + ")", navilog.ERROR)
		except ValueError:
			self._bot.log.write("Não foi possível converter o arquivo de configurações em um objeto JSON", navilog.ERROR)

	def get(self, indice):
		chaves = indice.split(".")
		atual = self._keys

		if len(chaves) <= 0:
			return
			
		try:
			for i in chaves:
				atual = atual[i]
		except KeyError:
			self._bot.log.write("Não foi possível encontrar a chave de configurações (" + indice + ")", navilog.WARNING)
			return ""

		return atual