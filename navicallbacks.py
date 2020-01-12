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
	activities = bot.config.get(f"global.bot_playing")
	delay = bot.config.get(f"global.bot_playing_delay")

	if not "loop" in kwargs:
		if not activities or not delay:
			return

		kwargs["loop"] = True
		kwargs["playing_index"] = 0
		kwargs["task"] = NaviRoutine(callbackActivity, timespan=(delay, "s"))
		kwargs["task"].kwargs = kwargs
		bot.tasks.schedule(kwargs["task"])
		return

	if activities != None:
		if isinstance(activities, list):
			if kwargs["playing_index"] >= len(activities):
				kwargs["playing_index"] = 0

			await bot.client.change_presence(activity=discord.Game(activities[kwargs["playing_index"]]))
			
			kwargs["playing_index"] = kwargs["playing_index"] + 1
		else:
			await bot.client.change_presence(activity=discord.Game(activities))


async def callbackError(bot, excInfo):
	bot.handle_exception(excInfo)

async def callbackCommandHandler(bot, message):
	if message.guild is None or message.author == bot.client.user or message.author.bot:
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