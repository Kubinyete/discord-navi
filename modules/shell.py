import re
import asyncio
import navibot

async def run_process(process, inpt, outpt):
	stdout, stderr = await process.communicate(input=inpt)

	outpt.append(stdout)
	outpt.append(stderr)

async def command_bc(bot, message, args, flags, handler):
	if len(args) < 2:
		await bot.feedback(message, feedback=navibot.COMMAND_INFO, usage=handler)
		return

	expr = " ".join(args[1:])

	process = await asyncio.create_subprocess_shell(f"bc -l", 
		stdin=asyncio.subprocess.PIPE, 
		stdout=asyncio.subprocess.PIPE, 
		stderr=asyncio.subprocess.PIPE
	)

	try:
		streams = []

		await asyncio.wait_for(
			run_process(process, bytes(f"scale=4;\n{expr}\n", encoding="utf-8"), streams)
		, timeout=5)
	except asyncio.TimeoutError as e:
		process.kill()
		bot.handle_exception(e)
	finally:
		if len(streams) > 0:
			stdout = streams[0].decode()
			stderr = streams[1].decode()

			if len(stdout) > 0:
				if len(stdout) > 2000:
					await bot.feedback(message, feedback=navibot.WARNING, text="O resultado da expressão é muito grande para ser mostrado")
				else:
					await bot.feedback(message, feedback=navibot.SUCCESS, text=stdout)
			else:
				if len(stderr) > 0:
					await bot.feedback(message, feedback=navibot.ERROR, text=stderr)
				else:
					await bot.feedback(message, feedback=navibot.INFO, text="Não foi retornado nenhuma saída do processo, ignorando...")