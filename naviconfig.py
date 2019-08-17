from navilog import LogType
import json

class ConfigManager:
	def __init__(self, configpath, logmanager):
		self.__configValues = {}
		self.__logManager = logmanager

		self.atualizarPath(configpath)
		self.carregarConfig()

	def atualizarPath(self, configpath):
		if type(configpath) != str:
			raise TypeError("'{}' não é uma str".format(configpath))

		self.__configPath = configpath
		
	def carregarConfig(self):
		try:
			with open(self.__configPath, "r", encoding="utf-8") as f:
				self.__configValues = json.loads("".join(f.readlines()))
				f.close()
		except IOError:
			self.__logManager.write("Não foi possível carregar o arquivo de configurações (" + self.__configPath + ")", LogType.ERROR)
		except ValueError:
			self.__logManager.write("Não foi possível converter o arquivo de configurações em um objeto JSON", LogType.ERROR)

	def obter(self, indice):
		chaves = indice.split(".")
		valorAtual = self.__configValues

		if len(chaves) <= 0:
			return

		try:
			for i in chaves:
				valorAtual = valorAtual[i]
		except KeyError:
			self.__logManager.write("Não foi possível encontrar a chave de configurações (" + indice + ")", LogType.ERROR)
			return None

		return valorAtual