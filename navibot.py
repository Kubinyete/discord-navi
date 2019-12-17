import asyncio
import discord
import platform
import sys
import tty
import termios
import importlib
import traceback
from naviclient import NaviClient
from navilog import LogManager
from naviconfig import ConfigManager
from navicommands import CommandDictionary
from navitasks import TaskScheduler

# Mensagem de texto padrão
INFO = 0
# Aconteceu um erro com o comando
ERROR = 1
# O comando foi bem sucedido
SUCCESS = 2
# O comando foi bem sucedido porém é algo perigoso
WARNING = 3	
# O comando não foi bem sucedido porém foi usado incorretamente
COMMAND_INFO = 4

def feedback_string(feedback):
	if feedback == INFO:
		return r"ℹ"
	elif feedback == ERROR:
		return r"❌"
	elif feedback == SUCCESS:
		return r"✅"
	elif feedback == WARNING:
		return r"⚠"
	else:
		return r"ℹ"

class NaviBot:
	def __init__(self, configpath, cli=True):
		# @NOTE
		# Só ativa o listener de CLI caso esteja no Linux
		# @TODO
		# Passar toda lógica de CLI para um componente específico, não poluir a classe principal
		self.cli_enabled = cli and platform.system() == "Linux"
		self.cli_buffer = ""
		self.cli_context = None

		self.log = LogManager("debug.log", self)
		self.config = ConfigManager(configpath, self)
		self.commands = CommandDictionary(self)
		self.tasks = TaskScheduler(self)
		self.http = None

		# Atualiza novamente o path para o especificado no arquivo de configurações
		self.log.set_path(self.config.get("global.log_path"))

		self.client = NaviClient(self)

	def _load_events_from_module(self, mdl):
		self.client.listen("on_ready", mdl.callbackLog)
		self.client.listen("on_ready", mdl.callbackActivity)
		#self.client.listen("on_ready", mdl.callbackCliListener)
		self.client.listen("on_message", mdl.callbackLog)
		#self.client.listen("on_message", mdl.callbackCommandHandler)
		self.client.listen("on_error", mdl.callbackError)

	def _load_commands_from_module(self, mdl):
		self.commands.load_from_module(mdl)

	def handle_exception(self, e):
		if type(e) == tuple:
			exctype = e[0]
			exc = e[1]
			excstack = e[2]
		else:
			exctype = type(e)
			exc = e
			excstack = traceback.format_exc()

		self.log.write("{bold.red}An exception has ocurred while running, please check the stack trace for more info.{reset}")
		self.log.write("{{bold.red}}{}{{reset}} : {{bold.white}}{}{{reset}}".format(exctype, exc))
		self.log.write("{{bold.white}}\n{}{{reset}}".format(excstack))
	
	def _load_module(self, modulo):
		if modulo in sys.modules:
			importlib.reload(sys.modules[modulo])
		else:
			try:
				importlib.import_module(modulo)
			except ImportError as e:
				self.handle_exception(e)
				return

		return sys.modules[modulo]

	def initialize(self):
		self.client.remove_all()
		self.config.load()

		self.prefix = self.config.get("global.bot_prefix")
		
		self._load_events_from_module(self._load_module("navicallbacks"))

		for mdlstr in self.config.get("global.bot_modules"):
			mdl = self._load_module(mdlstr)

			if mdl != None:
				self._load_commands_from_module(mdl)

	async def interpret_command(self, message, args, flags):
		h = self.commands.get(args[0])

		if h == None:
			return

		if not h.enabled:
			await self.feedback(message, WARNING, text="Este comando está atualmente desativado")
		elif h.owneronly and not self.is_owner(message.author):
			await self.feedback(message, WARNING, text="Você não ter permissão para realizar esta ação")
		else:
			await h.run(self, message, args, flags)

	async def interpret_cli(self, cliargs, cliflags):
		h = self.commands.get(cliargs[0])

		if h == None:
			return

		await h.run(self, None, cliargs, cliflags)
	
	async def fetch_json(self, url, params):
		return await self.http.request_json(url, params)

	def is_owner(self, author):
		return author.id in self.config.get("commands.owners")

	def start(self):
		self.initialize()

		# CLI está ativada?
		if self.cli_enabled:
			cli_stdin_saved_attr = termios.tcgetattr(sys.stdin)
			cli_stdin_current_attr = termios.tcgetattr(sys.stdin)
			
			# Desativa o ECHO do console
			cli_stdin_current_attr[3] = cli_stdin_current_attr[3] & ~termios.ECHO
			# Desativa o modo CANONICAL do console
			cli_stdin_current_attr[3] = cli_stdin_current_attr[3] & ~termios.ICANON
			# Aplica as modificações
			termios.tcsetattr(sys.stdin, termios.TCSANOW, cli_stdin_current_attr)

		try:
			self.client.navi_start(self.config.get("global.bot_token"))
		except Exception as e:
			self.handle_exception(e)
		finally:
			if self.cli_enabled:
				# Retorna como o terminal estava anteriormente
				termios.tcsetattr(sys.stdin, termios.TCSANOW, cli_stdin_saved_attr)

	async def stop(self):
		self.log.set_path("")
		self.log.close()
		await self.http.close()
		await self.client.navi_stop()

	# @SECTION
	# Funções auxiliares dos comandos do bot
	
	async def feedback(self, message, feedback=SUCCESS, title=None, text=None, code=False, exception=None):
		await message.add_reaction(feedback_string(feedback))

		if text != None:
			embed = None

			if type(code) == str:
				text = "```{}\n{}```".format(code, text)
			elif code:
				text = "```\n{}```".format(text)
			else:
				if title != None:
					embed = discord.Embed(title=title, description=text, color=discord.Colour.purple())
				else:
					embed = discord.Embed(description=text, color=discord.Colour.purple())

				embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

			if embed != None:
				await message.channel.send(embed=embed)
			else:
				await message.channel.send(text)

		if exception != None:
			self.handle_exception(exception)