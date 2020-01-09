import discord
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
		bot.tasks.schedule(NaviRoutine(callbackActivity, timespan=(bot.config.get(f"global.bot_playing_delay"), "s"), kwargs=kwargs))
		return

	activities = bot.config.get(f"global.bot_playing")

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

# @SECTION
# Dicionário de eventos para atribuir

LISTEN = {
	"on_ready": [
		callbackLog, 
		callbackActivity
	],
	"on_message": [
		callbackLog, 
		callbackCommandHandler
	],
	"on_error": [
		callbackError
	]
}