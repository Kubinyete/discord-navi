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
	__expr = "[{}] <{}> {}"
	__exprTextChannel = "{{yellow}}{guild}{{reset}} #{{red}}{channel}{{reset}} ({channelid}) {{bold}}{user}{{reset}} : "
	__exprDMChannel = "{{magenta}}{user}{{reset}}> ({userid}): "
	
	def __init__(self, logpath):
		self.__enabled = True
		self.atualizarPath(logpath)

	def atualizarPath(self, logpath):
		self.__path = logpath
		self.__erro = False

	def write(self, msg, logtype=LogType.INFO):
		msgBuffer = ""

		if type(msg) == str:
			msgBuffer = naviuteis.traduzirCores(self.__expr.format(str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")), LogType.toString(logtype), msg))
		elif type(msg) == discord.Message:
			if type(msg.channel) == discord.DMChannel:
				msgBuffer = naviuteis.traduzirCores(self.__expr.format(str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")), LogType.toString(logtype), self.__exprDMChannel.format(user=msg.author.name, userid=msg.author.id))) + msg.content
			else:
				msgBuffer = naviuteis.traduzirCores(self.__expr.format(str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")), LogType.toString(logtype), self.__exprTextChannel.format(guild=msg.channel.guild.name, channel=msg.channel.name, channelid=msg.channel.id, user=msg.author.name))) + msg.content
		else:
			raise TypeError("Tipo de 'msg' desconhecido")

		print(msgBuffer)

		if self.__enabled:
			try:
				with open(self.__path, "a", encoding="utf-8") as f:
					f.write(re.sub("\033\[[0-9]+(;[0-9]+)*m", "", msgBuffer) + "\n")
					f.close()
				
				self.__erro = False
			except IOError:
				if not self.__erro:
					self.__erro = True

					self.write("Não foi possível escrever no arquivo de log especificado (" + self.__path + ")", LogType.ERROR)
