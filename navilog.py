from datetime import datetime
import re
import discord
import sys
import naviuteis

LOGTYPE_STRING = [
	r"{bold.white}Debug{reset}",
	r"{bold.white}Informação{reset}",
	r"{bold.yellow}Aviso{reset}",
	r"{bold.red}Erro{reset}",
	r"{bold.white}Mensagem{reset}"
]

DEBUG = 0
INFO = 1
WARNING = 2
ERROR = 3
MESSAGE = 4

def logtype_string(logtype):
	return LOGTYPE_STRING[logtype]

class LogManager:
	EXPR_LOG = "[{}] <{}> {}"
	
	EXPR_TEXTCHANNEL = "{{yellow}}{guild}{{reset}} #{{red}}{channel}{{reset}} ({channelid}) {{bold}}{user}{{reset}} : "
	EXPR_DMCHANNEL = "{{magenta}}{user}{{reset}} ({userid}) : "
	
	EXPR_CLIINPUT = "{context} $ "
	
	def __init__(self, path, bot):
		self._file = None
		self._cli_chars_on_screen = 0
		self._bot = bot

		self.set_path(path)

	def get_context_string(self):
		if type(self._bot.cli_context) == discord.User:
			return "@{}".format(self._bot.cli_context.name)
		elif type(self._bot.cli_context) == discord.TextChannel:
			return "#{}".format(self._bot.cli_context.name)
		elif type(self._bot.cli_context) == discord.Guild:
			return "[{}]".format(self._bot.cli_context.name)
		else:
			return ""

	def set_path(self, path):
		self._path = path
		self._error = False
		
		self.enabled = len(path) > 0

	def close(self):
		if self._file != None:
			self._file.flush()
			self._file.close()
			self._file = None

	def draw_input(self, keep_input=False):
		if len(self._bot.cli_buffer) < self._cli_chars_on_screen:
			# Resetou com Enter ou Backspace
			
			sys.stdout.write("\033[1G")														# Vai para o inicio da linha
			sys.stdout.write("\033[0K")														# Limpa a linha atual (pode conter um Input anterior)
			sys.stdout.write(self.EXPR_CLIINPUT.format(context=self.get_context_string()))	# Imprime o Input do usuário
			
			# Solicita para a função abaixo desenhar tudo que esteja disponível
			self._cli_chars_on_screen = 0

		for i in self._bot.cli_buffer[self._cli_chars_on_screen:]:
			sys.stdout.write(i)
			self._cli_chars_on_screen = self._cli_chars_on_screen + 1

		if keep_input:
			sys.stdout.write("\n")
			self._cli_chars_on_screen = 0
			self.draw_input()

		sys.stdout.flush()

	def write(self, msg, logtype=INFO):
		msg_buffer = ""
		data = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

		if type(msg) == str:
			msg_buffer = naviuteis.translate_sequences(self.EXPR_LOG.format(data, logtype_string(logtype), msg))
		elif type(msg) == discord.Message:
			if type(msg.channel) == discord.DMChannel:
				msg_buffer = naviuteis.translate_sequences(self.EXPR_LOG.format(data, logtype_string(logtype), self.EXPR_DMCHANNEL.format(user=msg.author.name, userid=msg.author.id))) + msg.content
			else:
				msg_buffer = naviuteis.translate_sequences(self.EXPR_LOG.format(data, logtype_string(logtype), self.EXPR_TEXTCHANNEL.format(guild=msg.channel.guild.name, channel=msg.channel.name, channelid=msg.channel.id, user=msg.author.name))) + msg.content

		if self._bot.cli_enabled:
			sys.stdout.write("\033[1G")														# Vai para o inicio da linha
			sys.stdout.write("\033[0K")														# Limpa a linha atual (pode conter um Input anterior)
			sys.stdout.write(msg_buffer + "\n")												# Imprime o conteudo do Log
			
			sys.stdout.write(self.EXPR_CLIINPUT.format(context=self.get_context_string()))	# Imprime o Input do usuário
			
			self._cli_chars_on_screen = 0
			
			self.draw_input()
		else:
			sys.stdout.write(msg_buffer + "\n")

		if self.enabled and logtype != DEBUG:
			if self._file == None:
				try:
					self._file = open(self._path, "a", encoding="utf-8")
				except IOError:
					if not self._error:
						self._error = True
						self.write("Não foi possível escrever no arquivo de log especificado (" + self._path + ")", logtype=ERROR)
			else:
				if self._file.name != self._path:
					self.close()
					self.write(msg, logtype)
				else:
					self._file.write(re.sub(r"\033\[[0-9]+(;[0-9]+)*m", "", msg_buffer) + "\n")
					self._error = False
	