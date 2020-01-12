"""Modulo responsável por definir o bot.

Attributes:
    COMMAND_INFO (int): Constante que define o tipo de feedback, usado para informações de comando.
    ERROR (int): Constante que defino o tipo de feedback de ERRO.
    INFO (int): Constante que defino o tipo de feedback de INFORMAÇÃO.
    SUCCESS (int): Constante que defino o tipo de feedback de SUCESSO.
    WARNING (int): Constante que defino o tipo de feedback de AVISO.
"""

import asyncio
import discord
import platform
import sys
import tty
import termios
import importlib
import traceback
import math
import naviuteis
import navilog
from naviclient import NaviCommand
from naviclient import NaviClient
from navilog import LogManager
from naviconfig import ConfigManager
from navicommands import CommandDictionary
from navitasks import TaskScheduler
from navihttp import HttpWorker
from databases import Database

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

async def get_last_user_from(reaction):
	"""Retorna o ultimo usuário que deu a reação atual.
	
	Args:
		reaction (Reaction): A reação do discord.
	
	Returns:
		User: O último usuário que deu a reação informada.
	"""

	return (
		await reaction.users().flatten()
	)[-1]

class Poll:
	def __init__(self, question, answers, request_message, timeout=60):
		self._question = question
		self._answers = answers
		self._timeout = timeout
		self._request_message = request_message
		self._displaying_message = None

		self._votes = {}
		self._finished = False

	def generate_current_embed(self):
		fanswers = "\n".join(
			[f"**{chr(i)}** - {self._answers[i - 65]}" for i in range(65, 65 + len(self._answers))]
		)

		item = EmbedItem(
			description=fanswers,
			title=f'"{self._question}"',
			author=f"{self._request_message.author.name} iniciou uma votação"
		)

		embed = item.generate()
		embed.set_footer(text=f"{self._request_message.author.name} - Essa votação será finalizada em {naviuteis.seconds_string(self._timeout)}", icon_url=self._request_message.author.avatar_url_as(size=32))

		return embed

	def generate_result_embed(self):
		results = self.get_results()
		total = sum(results)

		if total > 0:
			description = "\n".join(
				[f"**{chr(65 + i)}** - {self._answers[i]}\n{results[i]} voto(s)" for i in range(len(results))]
			)
		else:
			description = f"A votação foi finalizada sem nenhum voto."

		item = EmbedItem(
			description=description,
			title=f'"{self._question}"',
			author=f"Resultados da votação"
		)

		embed = item.generate()
		embed.set_footer(text=f"{self._request_message.author.name} - {total} voto(s)", icon_url=self._request_message.author.avatar_url_as(size=32))

		return item.generate()

	def get_results(self):
		results = [0 for i in range(len(self._answers))]

		for vote in self._votes.values():
			results[vote] += 1

		return results

	async def callbackPollReact(self, bot, reaction, user):
		if self._finished or reaction.message.id != self._displaying_message.id or await get_last_user_from(reaction) == bot.client.user:
			return

		voteindex = ord(reaction.emoji) - ord(r"🇦") if isinstance(reaction.emoji, str) else -1

		if voteindex >= 0 and voteindex < len(self._answers):
			self._votes[user.id] = voteindex

	async def callbackPollRemoveReact(self, bot, reaction, user):
		if self._finished or reaction.message.id != self._displaying_message.id:
			return

		voteindex = ord(reaction.emoji) - ord(r"🇦") if isinstance(reaction.emoji, str) else -1

		if voteindex >= 0 and voteindex < len(self._answers):
			if user.id in self._votes and self._votes[user.id] == voteindex:
				del self._votes[user.id]

	async def send_and_wait(self, bot):
		embed = self.generate_current_embed()

		self._displaying_message = await self._request_message.channel.send(embed=embed)

		firstunicode = ord(r"🇦")
		for i in range(len(self._answers)):
			asyncio.get_running_loop().create_task(self._displaying_message.add_reaction(chr(firstunicode + i)))

		callback_name = f"callbackPollReactFor{self._displaying_message.id}"
		callback_name2 = f"callbackPollRemoveReactFor{self._displaying_message.id}"
		
		bot.client.listen("on_reaction_add", self.callbackPollReact, callback_name)
		bot.client.listen("on_reaction_remove", self.callbackPollRemoveReact, callback_name2)
		
		await asyncio.sleep(self._timeout)
		self._finished = True
		
		bot.client.remove("on_reaction_add", self.callbackPollReact, callback_name)
		bot.client.remove("on_reaction_remove", self.callbackPollRemoveReact, callback_name2)
		
		embed = self.generate_result_embed()
		await self._request_message.channel.send(embed=embed)

class EmbedItem:
	def __init__(self, description="", title="", url="", footer="", color=discord.Colour.purple(), image="", thumbnail="", author=(), fields=[]):
		"""Define um item de uma coleção de itens de slide, possui propriedades do objeto Embed do discord.
		
		Args:
		    description (str, optional): O texto da descrição.
		    title (str, optional): O título do embed.
		    url (str, optional): O url presente no título.
			footer (tuple(str, str?), str, optional): Uma tuple contendo (text, icon_url) ou apenas uma string.
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
		self.footer = footer

	def generate(self):
		embed = discord.Embed()
		embed.description = self.description
		embed.title = self.title
		embed.url = self.url
		embed.colour = self.color

		if len(self.image) > 0:
			embed.set_image(url=self.image)
			
		if len(self.thumbnail):
			embed.set_thumbnail(url=self.thumbnail)

		if isinstance(self.author, tuple):
			if len(self.author) > 0:
				if len(self.author) == 2:
					embed.set_author(name=self.author[0], url=self.author[1])
				elif len(self.author) == 3:
					embed.set_author(name=self.author[0], url=self.author[1], icon_url=self.author[2])
				else:
					embed.set_author(name=self.author[0])
		elif isinstance(self.author, str):
			embed.set_author(name=self.author)

		for field in self.fields:
			if len(field) == 3:
				embed.add_field(name=field[0], value=field[1], inline=field[2])
			else:
				embed.add_field(name=field[0], value=field[1], inline=False)

		if isinstance(self.footer, tuple):
			if len(self.footer) > 0:
				if len(self.footer) == 2:
					embed.set_footer(text=self.footer[0], icon_url=self.footer[1])
				else:
					embed.set_footer(text=self.footer[0])
		elif isinstance(self.footer, str):
			embed.set_footer(text=self.footer)

		return embed

class EmbedSlide:
	def __init__(self, items, request_message, start=0, timeout=60, right_reaction=r"▶️", left_reaction=r"◀️", restricted=False):
		"""Define um Embed navegável através de reações do usuário.
		
		Args:
		    items (list(EmbedItem)): Os itens a serem mostrados, cada item é um EmbedItem.
		    request_message (TYPE): A mensagem que originou o pedido do slide, será utilizado para enviar o embed.
		    start (int, optional): Inicia na posição informada.
		    timeout (int, optional): Define em segundos quanto tempo esperar por atividade de uso.
		    right_reaction (str, optional): O emoji que deverá ser utilizado para detectar o movimento para frente.
		    left_reaction (str, optional): O emoji que deverá ser utilizado para detectar o movimento para trás.
			restricted (bool, optional): Caso ativado, o slide será restrito à ser utilizado somente pelo solicitante da mensagem.
		"""

		self._items = items
		self._timeout = timeout
		self._index = start
		self._request_message = request_message
		self._callback_name = None
		self._displaying_message = None
		self._in_use = True
		self._restricted = restricted

		self.right_reaction = right_reaction
		self.left_reaction = left_reaction

	async def callbackEmbedSlideReact(self, bot, reaction, user):
		# @BUG:
		# reaction.me apenas retorna verdadeiro com base no primeiro usuário que deu a reação (que no caso é sempre o próprio bot)
		# Para evitar isso, é utilizado a função get_last_user_from(reaction) para obter a lista completa de pessoas que reagiram e retornando
		# o ultimo usuário que consequentemente será o gerador do evento
		last_react_user = await get_last_user_from(reaction)

		if reaction.message.id != self._displaying_message.id or last_react_user == bot.client.user or self._restricted and last_react_user != self._request_message.author:
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
		"""Retorna o EmbedItem atual.
		
		Returns:
		    EmbedItem: Item atual.
		"""

		return self._items[self._index]

	def generate_current_embed(self):
		"""Cria e configura o embed a ser mostrado atualmente.
		
		Returns:
		    Embed: O embed a ser enviado.
		"""

		embed = self.get_current_item().generate()
		embed.set_footer(text=f"{self._request_message.author.name} - {self._index + 1}/{len(self._items)}", icon_url=self._request_message.author.avatar_url_as(size=32))

		return embed

	async def send_and_wait(self, bot):
		"""Envia como resposta o slide, possibilitando que o usuário navegue utilizando as reações.
		
		Args:
		    bot (NaviBot): O bot responsável pela instância deste slide.
		"""

		embed = self.generate_current_embed()

		self._displaying_message = await self._request_message.channel.send(embed=embed)
		self._callback_name = f"callbackEmbedSlideFor{self._displaying_message.id}"

		asyncio.get_running_loop().create_task(self._displaying_message.add_reaction(self.left_reaction))
		asyncio.get_running_loop().create_task(self._displaying_message.add_reaction(self.right_reaction))

		bot.client.listen("on_reaction_add", self.callbackEmbedSlideReact, self._callback_name)

		while self._in_use:
			self._in_use = False
			await asyncio.sleep(self._timeout)

		bot.client.remove("on_reaction_add", self.callbackEmbedSlideReact, self._callback_name)

class GuildSettingsManager:
	def __init__(self, bot):
		self._guilds = {}
		self._bot = bot

	def get_all_keys(self):
		return self._guilds.keys()

	async def get_database_connection(self):
		return await self._bot.get_database_connection()
		
	async def get_settings(self, guild):
		default_global_settings = self._bot.config.get(f"database.guild_settings.default_global_guild_settings")

		if guild.id in self._guilds.keys():
			if self._guilds[guild.id].keys() == default_global_settings.keys():
				return self._guilds[guild.id]
			else:
				# Obsoleto
				return dict(default_global_settings)
		else:
			await self.fetch(guild)

			if guild.id in self._guilds.keys():
				if self._guilds[guild.id].keys() == default_global_settings.keys():
					return self._guilds[guild.id]
				else:
					# Obsoleto
					return dict(default_global_settings)
			else:
				return dict(default_global_settings)

	async def update_settings(self, guild, settings):
		conn = await self.get_database_connection()

		self._guilds[guild.id] = settings

		kvs = [
			{
				"id": guild.id, 
				"key": key, 
				"value": str(value), 
				"valuetype": self.translate_type_valuetype(value)
			} 
			for key, value in settings.items()
		]

		async with conn.transaction():
			await conn.execute(
				query="DELETE FROM guild_settings WHERE gui_id = :id",
				values={
					"id": guild.id
				}
			)

			await conn.execute_many(
				query="INSERT INTO guild_settings (gui_id, gst_key, gst_value, gst_value_type) VALUES (:id, :key, :value, :valuetype)",
				values=kvs
			)
	
	async def fetch(self, guild):
		conn = await self.get_database_connection()

		rows = await conn.fetch_all(
			query="""SELECT gst_key, gst_value, gst_value_type FROM guild_settings WHERE gui_id = :id""",
			values={
				"id": guild.id
			}
		)

		self._guilds[guild.id] = {}
		for row in rows:
			self._guilds[guild.id][row['gst_key']] = self.translate_key_value(row['gst_value'], row['gst_value_type'])

	@staticmethod
	def translate_key_value(value, value_type):
		if value_type == 1:
			return value.lower() in ("yes", "true", "1")
		elif value_type == 2:
			return int(value)
		elif value_type == 3:
			return float(value)
		
		return str(value)

	@staticmethod
	def translate_type_valuetype(value):
		if isinstance(value, bool):
			return 1
		elif isinstance(value, int):
			return 2
		elif isinstance(value, float):
			return 3

		return 0

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

		self._active_database_connection = None

		self.guildsettings = GuildSettingsManager(self)

		# Atualiza novamente o path para o especificado no arquivo de configurações
		self.log.set_path(self.config.get(f"global.log_path"))
		# Inicializa o cliente
		self.client = NaviClient(self)

	async def get_database_connection(self):
		if self._active_database_connection is None:
			try:
				self._active_database_connection = Database(self.config.get(f"database.connection.connection_string"))
				await self._active_database_connection.connect()
			except Exception as e:
				self.handle_exception(e)
				self._active_database_connection = None
		
		return self._active_database_connection

	async def close_database_connection(self):
		if self._active_database_connection is not None:
			try:
				await self._active_database_connection.disconnect()
				self._active_database_connection = None
			except Exception as e:
				self.handle_exception(e)

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
		for key, value in module.__dict__.items():
			if asyncio.iscoroutinefunction(value):
				if key.startswith("cli_"):
					atv = key[len("cli_"):]
					
					self.clicommands.set(
						atv, 
						NaviCommand(
							value, 
							name=atv, 
							usage=self.config.get(f"cli.{atv}.usage")
						)
					)
				elif key.startswith("command_owner_"):
					atv = key[len("command_owner_"):]
					
					self.commands.set(
						atv, 
						NaviCommand(
							value, 
							name=atv, 
							owneronly=True, 
							usage=self.config.get(f"commands.{atv}.usage"), 
							description=self.config.get(f"commands.{atv}.text")
						)
					)
				elif key.startswith("command_"):
					atv = key[len("command_"):]

					cmdperms = self.config.get(f"commands.{atv}.permissions")

					self.commands.set(
						atv, 
						NaviCommand(
							value, 
							name=atv, 
							owneronly=False, 
							usage=self.config.get(f"commands.{atv}.usage"), 
							description=self.config.get(f"commands.{atv}.text"),
							permissions=cmdperms if cmdperms else []
						)
					)

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
			#importlib.reload(sys.modules[modulo])

			del sys.modules[modulo]
			importlib.import_module(modulo)
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
		self.commands.clear()
		self.clicommands.clear()
		self.tasks.clear()

		self.config.load()

		self.prefix = self.config.get(f"global.bot_prefix")
		if not self.prefix:
			self.prefix = ";;"
		
		# Carrega os callbacks do núcleo novamente...
		self._load_events_from_module(self._load_module("navicallbacks"))

		# Carrega todos os modulos a serem acoplados...
		for mdlstr in self.config.get(f"global.bot_modules"):
			mdl = self._load_module(mdlstr)

			if mdl != None:
				self._load_events_from_module(mdl)
				self._load_commands_from_module(mdl)

	async def reload(self):
		self.initialize()
		await self.client.on_reload()

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
			await self.feedback(message, WARNING, text="Você não tem permissão para realizar esta ação")
		else:
			if h.permissions:
				perms = message.channel.permissions_for(message.author)

				for perm_name in h.permissions:
					if not (perm_name, True) in perms:
						await self.feedback(message, WARNING, text="Você as permissões necessárias para realizar esta ação")
						return

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

		return author.id in self.config.get(f"global.bot_owners")

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

			self.client.navi_start(self.config.get(f"global.bot_token"))
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
		await self.close_database_connection()
		await self.http.close()
		await self.client.navi_stop()

	# @SECTION
	# Funções auxiliares dos comandos do bot
	
	async def feedback(self, message, feedback=SUCCESS, title=None, text=None, code=False, exception=None, usage=None, embeditem=None):
		"""Devolve uma resposta padrão para uma ação do bot.
		
		Args:
		    message (Message): A mensagem do discord que originou as ações.
		    feedback (int, optional): O tipo de feedback para devolver.
		    title (str, optional): O título do embed.
		    text (str, optional): O texto a ser escrito no embed.
		    code (bool, str, optional): Define se será utilizado um bloco de código para escrever o texto definido em text.
		    exception (Exception, optional): Devolve uma resposta padrão para o usuário caso ocorra uma exception, imprimindo na CLI também.
		    usage (NaviCommand, optional): O handler contendo a informação de uso.
			embeditem (EmbedItem, optional): O EmbedItem a ser gerado e enviado como resposta.
		"""

		if feedback:
			await message.add_reaction(feedback_string(feedback))

		if embeditem:
			await message.channel.send(embed=embeditem.generate())
		else:
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