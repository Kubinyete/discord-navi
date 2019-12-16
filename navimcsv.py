import discord
import asyncio
import navibot
import subprocess
from navilog import LogType
from naviclient import NaviRoutine

class ServerInstance:
	__instancia = None

	@staticmethod
	def store(process):
		ServerInstance.__instancia = process

	@staticmethod
	def terminate():
		if ServerInstance.__instancia != None:
			ServerInstance.__instancia.terminate()

	@staticmethod
	def kill():
		if ServerInstance.__instancia != None:
			ServerInstance.__instancia.kill()

	@staticmethod
	def isStored():
		return ServerInstance.__instancia != None

	def isTerminated():
		if ServerInstance.isStored():
			return ServerInstance.__instancia.poll() != None

		return True

async def command_owner_mcsv(bot, h, client, message, args, flags):
	if len(args) < 2 and not "start" in flags and not "stop":
		await bot.sendFeedback(message, navibot.NaviFeedback.COMMAND_INFO, text=h.getUsage())
		return

	msg = None

	try:
		if "start" in flags:
			if ServerInstance.isTerminated():
				ServerInstance.store(subprocess.Popen([bot.configManager.obter("external.mcsv.java_path")] + bot.configManager.obter("external.mcsv.java_args"), cwd=bot.configManager.obter("external.mcsv.mcsv_path"), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
				msg = "Iniciando o processo..."
			else:
				await bot.sendFeedback(message, navibot.NaviFeedback.WARNING, text="O servidor já está atualmente rodando em segundo plano")
				return
		else:
			ServerInstance.terminate()
			msg = "Terminando o processo..."
	except Exception as e:
		await bot.sendFeedback(message, navibot.NaviFeedback.ERROR, exception=e)
		return

	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS, text=msg)