import discord
import sys
import select
import navilog
import naviuteis
from naviclient import NaviRoutine

# @SECTION
# Esse modulo fica responsável por servir de container para um set de comandos no qual a classe principal NaviBot irá examinar e referenciar as funções que estão aqui

async def callbackLog(bot, message=None):
	if not message:
		bot.log.write("O bot foi iniciado com sucesso")
	else:
		bot.log.write(message, logtype=navilog.MESSAGE)

async def callbackActivity(bot, kwargs={}):
	if not "loop" in kwargs:
		kwargs["loop"] = True
		kwargs["playing_index"] = 0
		await bot.tasks.schedule(NaviRoutine(callbackActivity, timespan=(bot.config.get("global.bot_playing_delay"), "s")), key=None, kwargs=kwargs)
		return

	activities = bot.config.get("global.bot_playing")

	if activities != None:
		if kwargs["playing_index"] >= len(activities):
			kwargs["playing_index"] = 0

		await bot.client.change_presence(activity=discord.Game(activities[kwargs["playing_index"]]))

		kwargs["playing_index"] = kwargs["playing_index"] + 1

async def callbackError(bot, excInfo):
	bot.handle_exception(excInfo)

async def callbackCommandHandler(bot, message):
	if message.author == bot.client.user or message.author.bot:
		return

	if message.content.startswith(bot.prefix):
		args, flags = naviuteis.get_args(message.content[len(bot.prefix):])

		if len(args) > 0:
			await bot.interpret_command(message, args, flags)

async def callbackCliListener(bot, kwargs={}):
	if not bot.cli_enabled:
		return

	if not "loop" in kwargs.keys():
		kwargs["loop"] = True
		await bot.tasks.schedule(NaviRoutine(callbackCliListener, timespan=(bot.config.get("cli.update_delay"), "ms")), key=None, kwargs=kwargs)
		return

	clilines = []

	while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
		c = sys.stdin.read(1)

		if c == '\n':
			if len(bot.cli_buffer) > 0:
				clilines.append(bot.cli_buffer)
				
				bot.log.draw_input(True)
				bot.cli_buffer = ""
		elif c == '\x7f':
			if len(bot.cli_buffer) > 0:
				bot.cli_buffer = bot.cli_buffer[:-1]
		elif c == '\x1b':
			pass
		else:
			bot.cli_buffer = bot.cli_buffer + c
		
		bot.log.draw_input()
		
	for l in clilines:
		cliargs, cliflags = naviuteis.get_args(l)

		if len(cliargs) > 0:
			await bot.interpret_cli(cliargs, cliflags)

async def callbackRemind(bot, kwargs):
	message = kwargs["message"]

	if "remind_text" in kwargs.keys():
		await message.author.send("<@{}> Estou lembrando para você de **{}**".format(message.author.id, kwargs["remind_text"]))
	else:
		await message.author.send("<@{}> Estou te lembrando de algo!".format(message.author.id))