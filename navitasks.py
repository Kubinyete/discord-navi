import asyncio
import naviclient
import navilog

class TaskScheduler:
	def __init__(self, bot):
		self._tasks = {}
		self._bot = bot

	async def schedule(self, task, key=None, append=False):
		if key is None:
			key = task.name

		if not key in self._tasks:
			self._tasks[key] = [task]
		else:
			if len(self._tasks[key]) == 0 or append:
				self._tasks[key].append(task)
			else:
				self._bot.log.write("A tarefa '{}' foi solicitada porém já existe".format(task.name), logtype=navilog.WARNING)
				return

		task.running_task = asyncio.get_running_loop().create_task(self._loopTask(task, key))

	async def _loopTask(self, task, key):
		try:
			segundos = task.get_timespan_seconds()

			while task.enabled:
				task.running = True

				await asyncio.sleep(segundos - task.get_timespent())

				if task.enabled:
					await task.run(self._bot)
					
					if task.get_timespent() >= segundos:
						self._bot.log.write("Perdido um ciclo de execução da tarefa '{}', timespent={:.3f}, timespan={}s".format(task.name, task.get_timespent(), segundos), logtype=navilog.WARNING)

			task.running = False
		except asyncio.CancelledError:
			self._bot.log.write("Cancelado a tarefa '{}'".format(task.name), logtype=navilog.WARNING)

			task.running_task = None
		finally:
			self.cancel(task, key)

	def cancel(self, task, key=None):
		if key is None:
			key = task.name

		if key in self._tasks.keys():
			if task.running_task != None and task.enabled:
				try:
					task.running_task.cancel()
				except asyncio.CancelledError:
					self._bot.log.write("Ignorando cancelamento da tarefa '{}' pois a mesma já foi cancelada".format(task.name), logtype=navilog.WARNING)
			try:
				self._tasks[key].remove(task)
			except ValueError:
				# Não está na lista
				pass

	def get(self, key):
		try:
			return self._tasks[key]
		except KeyError:
			return []