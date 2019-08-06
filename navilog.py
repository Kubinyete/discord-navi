from datetime import datetime
import enum

class LogType(enum.Enum):
	DEBUG = 0
	INFO = 1
	WARNING = 2
	ERROR = 3
	MESSAGE = 4

	@staticmethod
	def toString(logtype):
		strings = [
			"Debug",
			"Informação",
			"Aviso",
			"Erro",
			"Mensagem"
		]

		if logtype.value >= len(strings):
			return ""

		return strings[logtype.value]

class LogManager:
	__expr = "{} [{}] {}\n"
	
	def __init__(self, logpath):
		self.__enabled = True
		self.atualizarPath(logpath)

	def atualizarPath(self, logpath):
		self.__path = logpath
		self.__erro = False

	def write(self, msg, logtype=LogType.INFO):
		msgBuffer = self.__expr.format(str(datetime.now().strftime("%d-%m-%Y %H:%M:%S")), LogType.toString(logtype), msg)
		
		print(msgBuffer, end="")

		if self.__enabled:
			try:
				with open(self.__path, "a", encoding="utf-8") as f:
					f.write(msgBuffer)
					f.close()
				
				self.__erro = False
			except IOError:
				if not self.__erro:
					self.__erro = True

					self.write("Não foi possível escrever no arquivo de log especificado (" + self.__path + ")", LogType.ERROR)
