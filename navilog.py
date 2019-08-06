from datetime import datetime
import re
import discord
import enum
import naviuteis

class LogType(enum.Enum):
	DEBUG = 0
	INFO = 1
	WARNING = 2
	ERROR = 3
	MESSAGE = 4

	@staticmethod
	def toString(logtype):
		strings = [
			r"{bold.white}Debug{reset}",
			r"{bold.white}Informação{reset}",
			r"{bold.yellow}Aviso{reset}",
			r"{bold.red}Erro{reset}",
			r"{bold.white}Mensagem{reset}"
		]

		if logtype.value >= len(strings):
			return ""

		return strings[logtype.value]

class LogManager:
	__expr = "[{}] <{}> {}\n"
	
	def __init__(self, logpath):
		self.__enabled = True
		self.atualizarPath(logpath)

	def atualizarPath(self, logpath):
		self.__path = logpath
		self.__erro = False

	def write(self, msg, logtype=LogType.INFO):
		msgBuffer = ""

		# @CLEAN:
		# Refazer isto pois esta muito feio ¯\_(ツ)_/¯

		if type(msg) == str:
			msgBuffer = self.__expr.format(str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")), naviuteis.traduzirCores(LogType.toString(logtype)), msg)
		elif type(msg) == discord.Message:
			if type(msg.channel) == discord.DMChannel:
				msgBuffer = self.__expr.format(str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")), naviuteis.traduzirCores(LogType.toString(logtype)), "{}: {}".format(naviuteis.traduzirCores(r"{magenta}" + msg.author.name + r"{reset}"), msg.content))
			else:
				msgBuffer = self.__expr.format(str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")), naviuteis.traduzirCores(LogType.toString(logtype)), "{}#{} > {}: {}".format(naviuteis.traduzirCores(r"{yellow}" + msg.channel.guild.name + r"{reset}"), naviuteis.traduzirCores(r"{red}" + msg.channel.name + r"{reset}"), naviuteis.traduzirCores(r"{magenta}" + msg.author.name + r"{reset}"), msg.content))
		else:
			raise TypeError("Tipo de 'msg' desconhecido")

		print(msgBuffer, end="")

		if self.__enabled:
			try:
				with open(self.__path, "a", encoding="utf-8") as f:
					f.write(re.sub("\033\[[0-9]+(;[0-9]+)*m", "", msgBuffer))
					f.close()
				
				self.__erro = False
			except IOError:
				if not self.__erro:
					self.__erro = True

					self.write("Não foi possível escrever no arquivo de log especificado (" + self.__path + ")", LogType.ERROR)
