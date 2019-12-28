import asyncio
import navilog

class TaskScheduler:
	def __init__(self, bot):
		"""Componente composto de um dicionário de rotinas, capaz de agendar uma rotina para ser executada de acordo com seu intervalo.
		
		Args:
		    bot (NaviBot): A instância do bot em questão.
		"""
		
		self._tasks = {}
		self._bot = bot

	def schedule(self, task, key=None, append=False):
		"""Recebe uma tarefa para ser agendada, ou seja, rodar em um loop a cada intervalo de tempo determinado.
		
		Args:
		    task (NaviRoutine): A rotina a ser rodada constantemente.
		    key (str, optional): Chave que identifica qual o conjunto de rotinas, caso omitida, será utilizado task.name.
		    append (bool, optional): Permitir mais de única rotina em um conjunto de rotinas.
		"""

		# Se a chave não for informada, utilizar o próprio nome da tarefa
		if key is None:
			key = task.name

		if not key in self._tasks:
			self._tasks[key] = [task]
		else:
			# Define que, caso append seja falso, apenas inclua uma única tarefa por chave
			if len(self._tasks[key]) == 0 or append:
				self._tasks[key].append(task)
			else:
				self._bot.log.write(f"A tarefa '{task.name}' foi solicitada, porém já existe", logtype=navilog.WARNING)
				return

		task.running_task = asyncio.get_running_loop().create_task(self._loopTask(task, key))

	async def _loopTask(self, task, key):
		"""Procedimento utilizado para continuar executando em loop a tarefa/rotina.
		
		Args:
		    task (NaviRoutine): A rotina a ser rodada constantemente.
		    key (str): Chave pertencente.
		"""

		try:
			segundos = task.get_timespan_seconds()

			while task.enabled:
				task.running = True

				await asyncio.sleep(segundos - task.get_timespent())

				if task.enabled:
					await task.run(self._bot)
					
					if task.get_timespent() >= segundos:
						self._bot.log.write(f"Perdido um ciclo de execução da tarefa '{task.name}', timespent={task.get_timespent():.3f}, timespan={segundos}s", logtype=navilog.WARNING)

			task.running = False
		except asyncio.CancelledError:
			self._bot.log.write(f"Cancelado a tarefa '{task.name}'", logtype=navilog.WARNING)
			task.running_task = None
		finally:
			# Tenta retirar do cojunto de rotinas.
			self.cancel(task, key)

	def cancel(self, task, key=None):
		"""Pede o cancelamento da tarefa, caso esteja em execução e também retira do conjunto de tarefas pertencente.
		
		Args:
		    task (NaviRoutine): A rotina a ser cancelada.
		    key (str, optional): A chave que representa o conjunto, caso omitida, será utilizado por padrão task.name.
		"""

		if key is None:
			key = task.name

		if key in self._tasks.keys():
			# Caso esteja já desabilitada, é só uma questão de tempo até ser cancelada, não faça nada.
			if task.running_task != None and task.enabled:
				try:
					task.running_task.cancel()
				except asyncio.CancelledError:
					self._bot.log.write(f"Ignorando cancelamento da tarefa '{task.name}' pois a mesma já foi cancelada", logtype=navilog.WARNING)

			try:
				self._tasks[key].remove(task)
			except ValueError:
				# Não está na lista
				pass

	def get(self, key):
		"""Retorna a lista de tarefas presente em uma chave.
		
		Args:
		    key (str): A chave presentando o conjunto.
		
		Returns:
		    list(NaviRoutine), None: Uma lista de rotinas, caso não exista nenhuma na determinada chave, retorna None.
		"""

		try:
			return self._tasks[key]
		except KeyError:
			return None

	def get_all_keys(self):
		"""Retorna todas as chaves existentes.
		
		Returns:
		    list(str): Lista de chaves presentes.
		"""

		return self._tasks.keys()