import asyncio
import discord
import platform
import sys
import tty
import termios
import importlib
import traceback
import navilog
from naviclient import NaviCommand
from naviclient import NaviClient
from navilog import LogManager
from naviconfig import ConfigManager
from navicommands import CommandDictionary
from navitasks import TaskScheduler
from navihttp import HttpWorker

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

class NaviImage:
	def __init__(self, image, title=None, description=None, url=None):
		self.image = image
		self.title = title
		self.description = description
		self.url = url

class NaviImageViewer:
	def __init__(self, images, request_message, title=None, description=None, url=None, start=0, timeout=60, right_reaction=None, left_reaction=None):
		self._images = images
		self._timeout = timeout
		self._index = start
		self._request_message = request_message
		self._displaying_message = None
		self._in_use = True

		self.right_reaction = r"▶️" if right_reaction is None else right_reaction
		self.left_reaction = r"◀️" if left_reaction is None else left_reaction
		self.title = title
		self.description = description
		self.url = url

	def forward(self):
		self._index += 1

		if self._index >= len(self._images):
			self._index = 0

		self._in_use = True

	def backward(self):
		self._index -= 1

		if self._index < 0:
			self._index = len(self._images) - 1

		self._in_use = True

	def get_current_image(self):
		return self._images[self._index]

	def get_current_title(self):
		currtitle = self.title
		currimg = self.get_current_image()

		if isinstance(currimg, NaviImage) and currimg.title != None:
			currtitle = currimg.title
		
		return currtitle

	def get_current_description(self):
		currdescription = self.description
		currimg = self.get_current_image()

		if isinstance(currimg, NaviImage) and currimg.description != None:
			currdescription = currimg.description

		return currdescription

	def get_current_url(self):
		currurl = self.url
		currimg = self.get_current_image()

		if isinstance(currimg, NaviImage) and currimg.url != None:
			currurl = currimg.url
		
		return currurl

	def get_current_embed(self, existing_embed=None):
		currimg = self.get_current_image()
		currtitle = self.get_current_title()
		currdescription = self.get_current_description()
		currurl = self.get_current_url()

		embed = discord.Embed(color=discord.Colour.purple()) if existing_embed is None else existing_embed
		embed.title = currtitle
		embed.description = currdescription
		embed.url = currurl

		embed.set_image(url=currimg.image if isinstance(currimg, NaviImage) else currimg)
		embed.set_footer(text="{} - <{}/{}>".format(self._request_message.author.name, self._index + 1, len(self._images)), icon_url=self._request_message.author.avatar_url_as(size=32))

		return embed

	async def get_last_user_from(self, reaction):
		return (await reaction.users().flatten())[-1]

	async def callbackImageViewerReact(self, bot, reaction, user):
		# @BUG: discord.py
		# reaction.me apenas retorna verdadeiro com base no primeiro usuário que deu a reação (que no caso é sempre o próprio bot)
		# @NOTE:
		# Para evitar isso, é utilizado a função get_last_user_from(reaction) para obter a lista completa de pessoas que reagiram e retornando
		# o ultimo usuário que consequentemente será o gerador do evento
		if reaction.message.id != self._displaying_message.id or await self.get_last_user_from(reaction) == bot.client.user:
			return

		if reaction.emoji == self.right_reaction:
			self.forward()
		elif reaction.emoji == self.left_reaction:
			self.backward()
		else:
			return

		embed = self.get_current_embed(self._displaying_message.embeds[0])
		callbackstr = f"callbackImageViewer_{self._displaying_message.id}"

		try:
			await self._displaying_message.edit(embed=embed)
			self._in_use = True
		except discord.Forbidden:
			bot.client.remove("on_reaction_add", self.callbackImageViewerReact, callbackstr)
		except discord.HTTPException as e:
			bot.handle_exception(e)

	async def send_and_wait(self, bot):
		embed = self.get_current_embed()

		self._displaying_message = await self._request_message.channel.send(embed=embed)

		await self._displaying_message.add_reaction(self.left_reaction)
		await self._displaying_message.add_reaction(self.right_reaction)

		callbackstr = f"callbackImageViewer_{self._displaying_message.id}"
		bot.client.listen("on_reaction_add", self.callbackImageViewerReact, callbackstr)

		while self._in_use:
			self._in_use = False
			await asyncio.sleep(self._timeout)

		bot.client.remove("on_reaction_add", self.callbackImageViewerReact, callbackstr)

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
		self.clicommands = CommandDictionary(self)
		self.tasks = TaskScheduler(self)
		self.http = HttpWorker(self)

		# Atualiza novamente o path para o especificado no arquivo de configurações
		self.log.set_path(self.config.get("global.log_path"))

		self.client = NaviClient(self)

	def _load_events_from_module(self, mdl):
		try:
			for evt in mdl.LISTEN.keys():
				if isinstance(mdl.LISTEN[evt], list):
					for i in mdl.LISTEN[evt]:
						self.client.listen(evt, i)
				else:
					self.client.listen(evt, mdl.LISTEN[evt])
		except AttributeError:
			self.log.write(f"O modulo '{mdl.__name__}' não possui o atributo LISTEN de tipo dict para atribuir eventos, ignorando...")

	def _load_commands_from_module(self, module):
		for k in module.__dict__:
			if asyncio.iscoroutinefunction(module.__dict__[k]):
				if k.startswith("cli_"):
					atv = k[len("cli_"):]
					self.clicommands.set(atv, NaviCommand(module.__dict__[k], name=atv, usage=self.config.get("cli.commands.descriptions.{}.usage".format(atv))))
				elif k.startswith("command_owner_"):
					atv = k[len("command_owner_"):]
					self.commands.set(atv, NaviCommand(module.__dict__[k], name=atv, owneronly=True, usage=self.config.get("commands.descriptions.{}.usage".format(atv)), description=self.config.get("commands.descriptions.{}.text".format(atv))))
				elif k.startswith("command_"):
					atv = k[len("command_"):]
					self.commands.set(atv, NaviCommand(module.__dict__[k], name=atv, owneronly=False, usage=self.config.get("commands.descriptions.{}.usage".format(atv)), description=self.config.get("commands.descriptions.{}.text".format(atv))))

	def handle_exception(self, e):
		if e is tuple:
			exctype = e[0]
			exc = e[1]
		else:
			exctype = type(e)
			exc = e
		
		excstack = traceback.format_exc()

		self.log.write("{bold.red}Uma exception ocorreu durante a execução, favor verificar a pilha de execução abaixo{reset}", logtype=navilog.ERROR)
		self.log.write("{{bold.red}}{}{{reset}} : {{bold.white}}{}{{reset}}".format(exctype, exc), logtype=navilog.ERROR)
		self.log.write("{{yellow}}{}{{reset}}".format(excstack), logtype=navilog.ERROR)
	
	def _load_module(self, modulo):
		if modulo in sys.modules:
			importlib.reload(sys.modules[modulo])
		else:
			try:
				importlib.import_module(modulo)
			except Exception as e:
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
				self._load_events_from_module(mdl)
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
		h = self.clicommands.get(cliargs[0])

		if h == None:
			return

		await h.run(self, None, cliargs, cliflags)

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

			if code is str:
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