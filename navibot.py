"""Modulo responsável por definir o bot.

Attributes:
    COMMAND_INFO (int): Constante que define o tipo de feedback, usado para informações de comando.
    ERROR (int): Constante que defino o tipo de feedback de ERRO.
    INFO (int): Constante que defino o tipo de feedback de INFORMAÇÃO.
    SUCCESS (int): Constante que defino o tipo de feedback de SUCESSO.
    WARNING (int): Constante que defino o tipo de feedback de AVISO.
"""

import asyncio
#import uvloop
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
	"""Representação do tipo de feedback em forma de string, mais específicamente emoji para reação.
	
	Args:
	    feedback (int): O tipo de feedback.
	
	Returns:
	    str: Reação correspondente.
	"""

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

class EmbedSlideItem:
	def __init__(self, description="", title="", url="", color=discord.Colour.purple(), image="", thumbnail="", author=(), fields=[]):
		"""Define um item de uma coleção de itens de slide, possui propriedades do objeto Embed do discord.
		
		Args:
		    description (str, optional): O texto da descrição.
		    title (str, optional): O título do embed.
		    url (str, optional): O url presente no título.
		    color (Colour, int, optional): A color utilizada.
		    image (str, optional): O url da imagem a ser mostrada.
		    thumbnail (str, optional): O url da minitura a ser mostrada.
		    author (tuple(str, str?, str?), str, optional): Uma tuple contendo (name, url, icon_url) ou apenas uma string.
		    fields (list(tuple(str, str, bool?)), optional): Uma lista de tuples contendo (name, value, inline)
		"""

		self.description = description
		self.title = title
		self.url = url
		self.color = color
		self.image = image
		self.thumbnail = thumbnail
		self.author = author
		self.fields = fields

class EmbedSlide:
	def __init__(self, items, request_message, start=0, timeout=60, right_reaction=r"▶️", left_reaction=r"◀️"):
		"""Define um Embed navegável através de reações do usuário.
		
		Args:
		    items (list(EmbedSlideItem)): Os itens a serem mostrados, cada item é um EmbedSlideItem.
		    request_message (TYPE): A mensagem que originou o pedido do slide, será utilizado para enviar o embed.
		    start (int, optional): Inicia na posição informada.
		    timeout (int, optional): Define em segundos quanto tempo esperar por atividade de uso.
		    right_reaction (str, optional): O emoji que deverá ser utilizado para detectar o movimento para frente.
		    left_reaction (str, optional): O emoji que deverá ser utilizado para detectar o movimento para trás.
		"""

		self._items = items
		self._timeout = timeout
		self._index = start
		self._request_message = request_message
		self._callback_name = None
		self._displaying_message = None
		self._in_use = True

		self.right_reaction = right_reaction
		self.left_reaction = left_reaction

	async def callbackEmbedSlideReact(self, bot, reaction, user):
		# @BUG:
		# reaction.me apenas retorna verdadeiro com base no primeiro usuário que deu a reação (que no caso é sempre o próprio bot)
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

		embed = self.generate_current_embed()

		try:
			await self._displaying_message.edit(embed=embed)
			self._in_use = True
		except discord.Forbidden:
			bot.client.remove("on_reaction_add", self.callbackEmbedSlideReact, self._callback_name)

	def forward(self):
		"""Avança o slide em uma posição.
		"""

		self._index += 1

		if self._index >= len(self._items):
			self._index = 0

	def backward(self):
		"""Recua o slide em uma posição.
		"""

		self._index -= 1

		if self._index < 0:
			self._index = len(self._items) - 1

	def get_current_item(self):
		"""Retorna o EmbedSlideItem atual.
		
		Returns:
		    EmbedSlideItem: Item atual.
		"""

		return self._items[self._index]

	def generate_current_embed(self):
		"""Cria e configura o embed a ser mostrado atualmente.
		
		Returns:
		    Embed: O embed a ser enviado.
		"""

		item = self.get_current_item()

		embed = discord.Embed()
		embed.description = item.description
		embed.title = item.title
		embed.url = item.url
		embed.colour = item.color

		if len(item.image) > 0:
			embed.set_image(url=item.image)
			
		if len(item.thumbnail):
			embed.set_thumbnail(url=item.thumbnail)

		if isinstance(item.author, tuple):
			if len(item.author) > 0:
				if len(item.author) == 2:
					embed.set_author(name=item.author[0], url=item.author[1])
				elif len(item.author) == 3:
					embed.set_author(name=item.author[0], url=item.author[1], icon_url=item.author[2])
				else:
					embed.set_author(name=item.author[0])
		elif isinstance(item.author, str):
			embed.set_author(name=item.author)

		for field in item.fields:
			if len(field) == 3:
				embed.add_field(name=field[0], value=field[1], inline=field[2])
			else:
				embed.add_field(name=field[0], value=field[1], inline=False)

		embed.set_footer(text=f"{self._request_message.author.name} - {self._index + 1}/{len(self._items)}", icon_url=self._request_message.author.avatar_url_as(size=32))

		return embed

	async def get_last_user_from(self, reaction):
		"""Retorna o ultimo usuário que deu a reação atual.
		
		Args:
		    reaction (Reaction): A reação do discord.
		
		Returns:
		    User: O último usuário que deu a reação informada.
		"""

		return (await reaction.users().flatten())[-1]

	async def send_and_wait(self, bot):
		"""Envia como resposta o slide, possibilitando que o usuário navegue utilizando as reações.
		
		Args:
		    bot (NaviBot): O bot responsável pela instância deste slide.
		"""

		embed = self.generate_current_embed()

		self._displaying_message = await self._request_message.channel.send(embed=embed)
		self._callback_name = f"callbackEmbedSlideFor{self._displaying_message.id}"

		await self._displaying_message.add_reaction(self.left_reaction)
		await self._displaying_message.add_reaction(self.right_reaction)

		bot.client.listen("on_reaction_add", self.callbackEmbedSlideReact, self._callback_name)

		while self._in_use:
			self._in_use = False
			await asyncio.sleep(self._timeout)

		bot.client.remove("on_reaction_add", self.callbackEmbedSlideReact, self._callback_name)

class NaviBot:
	def __init__(self, configpath, cli=True):
		"""Inicializa uma instância NaviBot.
		
		Args:
		    configpath (str): O caminho utilizado para encontrar o arquivo JSON de configurações.
		    cli (bool, optional): Habilita o uso da CLI interativa.
		"""
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
		# Inicializa o cliente
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
		"""Imprime de forma verbosa a Exception recebida.
		
		Args:
		    e (Exception): A exceção a ser imprimida.
		"""
		if isinstance(e, tuple):
			exctype = e[0]
			exc = e[1]
		else:
			exctype = type(e)
			exc = e
		
		excstack = traceback.format_exc()

		self.log.write(f"{{bold.red}}Uma exception ocorreu durante a execução, favor verificar a pilha de execução abaixo{{reset}}", logtype=navilog.ERROR)
		self.log.write(f"{{bold.red}}{exctype}{{reset}} : {{bold.white}}{exc}{{reset}}", logtype=navilog.ERROR)
		self.log.write(f"{{yellow}}{excstack}{{reset}}", logtype=navilog.ERROR)
	
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
		"""Inicializa todos os componentes envolvidos.
		"""

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
		"""Interpreta um comando, encontrando com base em seus args e flags o seu handler responsável por executá-lo.
		
		Args:
		    message (Message): A mensagem de origem do discord.
		    args (list(str)): A lista de argumentos.
		    flags (dict): O dicionário de flags.
		"""

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
		"""Interpreta um comando CLI, encontrando com base em seus args e flags o seu handler responsável por executá-lo.
		
		Args:
		    cliargs (list(str)): A lista de argumentos.
		    cliflags (dict): O dicionário de flags.
		"""

		h = self.clicommands.get(cliargs[0])

		if h == None:
			return

		await h.run(self, None, cliargs, cliflags)

	def is_owner(self, author):
		"""Retorna se determinado usuário é um dono específicado no arquivo de configurações.
		
		Args:
		    author (User): O usuário autor da mensagem.
		
		Returns:
		    bool: Retorna se é um autor definido.
		"""

		return author.id in self.config.get("commands.owners")

	def start(self):
		"""Inicia o bot, bloqueando a execução de outros procedimentos e executando somente o loop de eventos.
		"""

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
			#uvloop.install()

			self.client.navi_start(self.config.get("global.bot_token"))
		except Exception as e:
			self.handle_exception(e)
		finally:
			if self.cli_enabled:
				# Retorna como o terminal estava anteriormente
				termios.tcsetattr(sys.stdin, termios.TCSANOW, cli_stdin_saved_attr)

	async def stop(self):
		"""Pede para o cliente deslogar, finalizando o loop de execução.
		"""

		self.log.set_path("")
		self.log.close()
		await self.http.close()
		await self.client.navi_stop()

	# @SECTION
	# Funções auxiliares dos comandos do bot
	
	async def feedback(self, message, feedback=SUCCESS, title=None, text=None, code=False, exception=None, usage=None):
		"""Devolve uma resposta padrão para uma ação do bot.
		
		Args:
		    message (Message): A mensagem do discord que originou as ações.
		    feedback (int, optional): O tipo de feedback para devolver.
		    title (str, optional): O título do embed.
		    text (str, optional): O texto a ser escrito no embed.
		    code (bool, str, optional): Define se será utilizado um bloco de código para escrever o texto definido em text.
		    exception (Exception, optional): Devolve uma resposta padrão para o usuário caso ocorra uma exception, imprimindo na CLI também.
		    usage (NaviCommand, optional): O handler contendo a informação de uso.
		"""

		await message.add_reaction(feedback_string(feedback))

		if usage != None:
			if isinstance(usage.usage, list):
				text = "\n".join([f"`{usage.name} {i}`" for i in usage.usage])
			else:
				text = f"`{usage.name} {usage.usage}`"

		if text != None:
			embed = None

			if isinstance(code, str):
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