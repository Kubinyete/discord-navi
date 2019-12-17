import discord
import navilog
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