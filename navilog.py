from datetime import datetime
import re
import discord
import enum
import naviuteis

LOG_STRING_VALUES = [
	r"{bold.white}Debug{reset}",
	r"{bold.white}Informação{reset}",
	r"{bold.yellow}Aviso{reset}",
	r"{bold.red}Erro{reset}",
	r"{bold.white}Mensagem{reset}"
]

class LogType(enum.Enum):
	DEBUG = 0
	INFO = 1
	WARNING = 2
	ERROR = 3
	MESSAGE = 4

	@staticmethod
	def toString(logtype):
		if type(logtype) != LogType:
			raise TypeError("'{}' não é um enum do tipo LogType")

		return LOG_STRING_VALUES[logtype.value]

class LogManager:
	EXPR_LOG = "[{}] <{}> {}"
	EXPR_TEXTCHANNEL = "{{yellow}}{guild}{{reset}} #{{red}}{channel}{{reset}} ({channelid}) {{bold}}{user}{{reset}} : "
	EXPR_DMCHANNEL = "{{magenta}}{user}{{reset}} ({userid}) : "
	
	def __init__(self, logpath):
		self.__file = None
		self.setAtivado(True)
		self.atualizarPath(logpath)

	def atualizarPath(self, logpath):
		if type(logpath) != str:
			raise TypeError("'{}' não é uma str".format(logpath))
			
		self.__path = logpath
		self.__erro = False

	def setAtivado(self, state):
		if type(state) != bool:
			raise TypeError("'{}' não é um bool".format(state))

		self.__enabled = state

	def obterAtivado(self):
		return self.__enabled

	def fechar(self):
		if self.__file != None:
			self.__file.flush()
			self.__file.close()
			self.__file = None

	def write(self, msg, logtype=LogType.INFO):
		msgBuffer = ""

		if type(msg) == str:
			msgBuffer = naviuteis.traduzirCores(self.EXPR_LOG.format(str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")), LogType.toString(logtype), msg))
		elif type(msg) == discord.Message:
			if type(msg.channel) == discord.DMChannel:
				msgBuffer = naviuteis.traduzirCores(self.EXPR_LOG.format(str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")), LogType.toString(logtype), self.EXPR_DMCHANNEL.format(user=msg.author.name, userid=msg.author.id))) + msg.content
			else:
				msgBuffer = naviuteis.traduzirCores(self.EXPR_LOG.format(str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")), LogType.toString(logtype), self.EXPR_TEXTCHANNEL.format(guild=msg.channel.guild.name, channel=msg.channel.name, channelid=msg.channel.id, user=msg.author.name))) + msg.content
		else:
			raise TypeError("Tipo de 'msg' desconhecido")

		print(msgBuffer)

		if self.__enabled and logtype != LogType.DEBUG:
			# @NOTE
			# Operação que congela a rotina atual
			
			if self.__file == None:
				try:
					self.__file = open(self.__path, "a", encoding="utf-8")
				except IOError:
					if not self.__erro:
						self.__erro = True

						self.write("Não foi possível escrever no arquivo de log especificado (" + self.__path + ")", LogType.ERROR)
			else:
				if self.__file.name != self.__path:
					self.fechar()
					self.write(msg, logtype)
				else:
					self.__file.write(re.sub("\033\[[0-9]+(;[0-9]+)*m", "", msgBuffer) + "\n")
					self.__erro = False
	