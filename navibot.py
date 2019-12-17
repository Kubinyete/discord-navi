import discord
import asyncio
import platform
import time
import sys
import tty
import termios
import importlib
import traceback
import naviclient
from navilog import LogManager
from naviconfig import ConfigManager
from navicommands import CommandDictionary

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

class NaviBot:
	def __init__(self, configpath, cli=True):
		self.log = LogManager("debug.log", self)
		self.config = ConfigManager(configpath, self)
		self.commands = CommandDictionary()
		self.tasks = TaskScheduler()

		self.log.set_path(self.config.get("global.log_path"))

		self.client = naviclient.NaviClient(self)

		# @NOTE
		# Só ativa o listener de CLI caso esteja no Linux
		self.cli_enabled = cli and platform.system() == "Linux"
		self.cli_buffer = ""
		self.cli_context = None

	def _load_events_from_module(self, mdl):
		self.client.listen("on_ready", mdl.callbackLog)
		#self.client.listen("on_ready", mdl.callbackActivity)
		#self.client.listen("on_ready", mdl.callbackCliListener)
		#self.client.listen("on_message", mdl.callbackLog)
		#self.client.listen("on_message", mdl.callbackCommandHandler)

	def _load_commands_from_module(self, mdl):
		self.commands.load_from_module(mdl)

	def _handle_exception(self, e):
		self.log.write("{bold.red}An exception has ocurred while running, please check the stack trace for more info.{reset}")
		self.log.write("{{bold.red}}{}{{reset}} : {{bold.yellow}}{}{{reset}}".format(str(type(e)), e))
		self.log.write("{bold.yellow}\n" + traceback.format_exc() + "{reset}")
	
	def _load_module(self, modulo):
		if modulo in sys.modules:
			importlib.reload(sys.modules[modulo])
		else:
			try:
				importlib.import_module(modulo)
			except ImportError as e:
				self._handle_exception(e)
				return

		return sys.modules[modulo]

	def initialize(self):
		self.client.remove_all()
		self.config.load()

		self.prefix = self.config.get("global.bot_prefix")
		self.playing_index = 0
		
		self._load_events_from_module(self._load_module("navicallbacks"))
		self._load_commands_from_module(self._load_module("navicommands"))

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
		return await self.http.request(url, params).json()

	def is_owner(self, author):
		return author.id in self.config.get("commands.owners")

	def start(self):
		self.initialize()

		# CLI está ativada?
		if self.cli_enabled:
			cli_stdin_saved_attr = termios.tcgetattr(sys.stdin)
			self.cli_stdin_current_attr = termios.tcgetattr(sys.stdin)
			
			# Desativa o ECHO do console
			self.cli_stdin_current_attr[3] = self.cli_stdin_current_attr[3] & ~termios.ECHO
			
			# Desativa o modo CANONICAL do console
			self.cli_stdin_current_attr[3] = self.cli_stdin_current_attr[3] & ~termios.ICANON
			
			# Aplica as modificações
			termios.tcsetattr(sys.stdin, termios.TCSANOW, self.cli_stdin_current_attr)

		try:
			self.client.start(self.config.get("global.bot_token"))
		except Exception as e:
			self._handle_exception(e)
		finally:
			if self.cli_enabled:
				termios.tcsetattr(sys.stdin, termios.TCSANOW, cli_stdin_saved_attr)

	async def stop(self):
		self.log.set_path("")
		self.log.close()
		await self.httpWorker.close()
		await self.client.stop()

	# @SECTION
	# Funções auxiliares dos comandos do bot
	
	async def feedback(self, message, feedback=SUCCESS, title=None, text=None, code=False, exception=None):
		if feedback == NaviFeedback.INFO:
			await message.add_reaction(r"ℹ")
		elif feedback == NaviFeedback.ERROR:
			await message.add_reaction(r"❌")
		elif feedback == NaviFeedback.SUCCESS:
			await message.add_reaction(r"✅")
		elif feedback == NaviFeedback.WARNING:
			await message.add_reaction(r"⚠")
		elif feedback == NaviFeedback.COMMAND_INFO:
			await message.add_reaction(r"ℹ")

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
			self._handle_exception(ex)