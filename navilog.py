"""Define todos os tipos de logs que o bot suporta através do seu LogManager.

Attributes:
    DEBUG (int): Constante que define um log do tipo DEBUG, não será gravado em disco.
    INFO (int): Constante que define um log de INFORMAÇÃO.
    WARNING (int): Constante que define um log de AVISO.
    ERROR (int): Constante que define um log de ERRO.
    MESSAGE (int): Constante que define um log de uma MENSAGEM.
"""

from datetime import datetime
import re
import discord
import sys
import naviuteis

DEBUG = 0
INFO = 1
WARNING = 2
ERROR = 3
MESSAGE = 4

LOGTYPE_STRING = [
	r"{bold.white}Debug{reset}",
	r"{bold.white}Informação{reset}",
	r"{bold.yellow}Aviso{reset}",
	r"{bold.red}Erro{reset}",
	r"{bold.white}Mensagem{reset}"
]

def logtype_string(logtype):
	"""Retorna a representação em string da constante que define o tipo de LOG.
	
	Args:
	    logtype (int): A constante que define o tipo de log.
	
	Returns:
	    str: Representação do tipo de log em string.
	"""

	return LOGTYPE_STRING[logtype]

class LogManager:
	EXPR_LOG = "[{}] <{}> {}"
	EXPR_TEXTCHANNEL = "{{yellow}}{guild}{{reset}} #{{red}}{channel}{{reset}} ({channelid}) {{bold}}{user}{{reset}} : "
	EXPR_DMCHANNEL = "{{magenta}}{user}{{reset}} ({userid}) : "
	EXPR_CLIINPUT = "{context} $ "
	
	def __init__(self, path, bot):
		"""Componente responsável por efetuar as operações de log do bot.
		
		Args:
		    path (str): O caminho do arquivo de log a ser utilizado.
		    bot (NaviBot): A instância do bot responsável.
		"""

		self._file = None
		self._bot = bot
		self._cli_chars_on_screen = 0

		self.set_path(path)

	def get_context_string(self):
		"""Retorna em que contexto o bot está atualmente em forma de string.
		
		Returns:
		    str: O contexto atual, caso não escolhido, retornará uma string vazia.
		"""

		if isinstance(self._bot.cli_context, discord.User):
			return "@{}".format(self._bot.cli_context.name)
		elif isinstance(self._bot.cli_context, discord.TextChannel):
			return "#{}".format(self._bot.cli_context.name)
		elif isinstance(self._bot.cli_context, discord.Guild):
			return "[{}]".format(self._bot.cli_context.name)
		else:
			return "NaviBot"

	def set_path(self, path):
		"""Atualiza o caminho do arquivo de log.
		
		Args:
		    path (str): Caminho a ser utilizado, caso será equivalente a "", a função de log será desativado.
		"""

		self._path = path
		self._error = False
		
		self.enabled = len(path) > 0

	def close(self):
		"""Fecha e libera o arquivo associado.
		"""

		if self._file != None:
			self._file.flush()
			self._file.close()
			self._file = None

	def draw_input(self, keep_input=False):
		"""Desenha na STDOUT como está o estado do input gráficamente.
		
		Args:
		    keep_input (bool, optional): Registra um input permanentemente na linha acima, simulando o envio de comando.
		"""

		if len(self._bot.cli_buffer) < self._cli_chars_on_screen:
			# Resetou com Enter ou Backspace

			# Vai para o inicio da linha
			sys.stdout.write("\033[1G")
			# Limpa a linha atual (pode conter um Input anterior)
			sys.stdout.write("\033[0K")
			# Imprime o Input do usuário
			sys.stdout.write(self.EXPR_CLIINPUT.format(context=self.get_context_string()))
			# Solicita para a função abaixo desenhar tudo que esteja disponível
			self._cli_chars_on_screen = 0

		for i in self._bot.cli_buffer[self._cli_chars_on_screen:]:
			sys.stdout.write(i)
			self._cli_chars_on_screen += 1

		if keep_input:
			sys.stdout.write("\n")
			self._cli_chars_on_screen = 0
			self.draw_input()

		sys.stdout.flush()

	def write(self, msg, logtype=INFO):
		"""Escreve, de acordo com o nivel/tipo de log, a mensagem.
		
		Args:
		    msg (Message, str): Uma mensagem do discord ou string a ser escrita.
		    logtype (int, optional): O tipo/nível de log.
		"""

		msg_buffer = ""
		data = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

		if isinstance(msg, str):
			msg_buffer = naviuteis.translate_sequences(self.EXPR_LOG.format(data, logtype_string(logtype), msg))
		elif isinstance(msg, discord.Message):
			if isinstance(msg.channel,  discord.DMChannel):
				msg_buffer = naviuteis.translate_sequences(self.EXPR_LOG.format(data, logtype_string(logtype), self.EXPR_DMCHANNEL.format(user=msg.author.name, userid=msg.author.id))) + msg.content
			else:
				msg_buffer = naviuteis.translate_sequences(self.EXPR_LOG.format(data, logtype_string(logtype), self.EXPR_TEXTCHANNEL.format(guild=msg.channel.guild.name, channel=msg.channel.name, channelid=msg.channel.id, user=msg.author.name))) + msg.content

		if self._bot.cli_enabled:
			# Vai para o inicio da linha
			sys.stdout.write("\033[1G")
			# Limpa a linha atual (pode conter um Input anterior)
			sys.stdout.write("\033[0K")
			# Imprime o conteudo do Log
			sys.stdout.write(msg_buffer + "\n")
			# Imprime o Input do usuário
			sys.stdout.write(self.EXPR_CLIINPUT.format(context=self.get_context_string()))
			
			# Reseta a quantidade de caracteres do input impressos.
			self._cli_chars_on_screen = 0
			# Solicita a impressão dos mesmos
			self.draw_input()
		else:
			sys.stdout.write(msg_buffer + "\n")

		# Logica para ver se podemos escrever em disco.
		if self.enabled and logtype != DEBUG:
			if self._file == None:
				try:
					self._file = open(self._path, "a", encoding="utf-8")
				except IOError:
					if not self._error:
						self._error = True
						# Recursivamente, chame a mesma função, só que agora para escrever somente na CLI que não podemos escrever em disco.
						self.write(f"Não foi possível escrever no arquivo de log especificado '{self._path}'", logtype=ERROR)
			else:
				if self._file.name != self._path:
					self.close()
					self.write(msg, logtype)
				else:
					# Retira todas as sequências ANSI antes de escrever em disco.
					self._file.write(re.sub(r"\033\[[0-9]+(;[0-9]+)*m", "", msg_buffer) + "\n")
					# Desativa qualquer estado de erro que tivemos anteriormente.
					self._error = False
	