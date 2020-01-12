import math

class MemberInfo:
	def __init__(self, member, **kwargs):
		self.member = member
		self.exp = kwargs.get('exp', 0)
		self.credits = kwargs.get('credits', 0)
		self.description = kwargs.get('description', '')

	def get_current_level(self):
		return math.floor(math.sqrt(2) * math.sqrt(self.exp) / 10.0)

	def get_exp_required(self):
		return self.get_exp_for_level(self.get_current_level() + 1) - self.exp

	@staticmethod
	def get_exp_for_level(level):
		return int(50 * math.pow(level, 2))

class ProgressionManager:
	unique_instance = None

	def __init__(self, bot):
		# @TODO?
		# Fazer um dict de cache para evitar consultas (semelhante ao GuildSettingsManager)?
		self._bot = bot
		self._levelup_listeners = []
		self._blocked = {}

	@staticmethod
	def get_instance(bot=None):
		if ProgressionManager.unique_instance is None and not bot is None:
			ProgressionManager.unique_instance = ProgressionManager(bot)

		return ProgressionManager.unique_instance

	async def get_database_connection(self):
		return await self._bot.get_database_connection()

	async def fetch_member_info(self, member):
		conn = await self.get_database_connection()

		row = await conn.fetch_one(
			query="SELECT mem_exp, mem_credits, mem_description FROM member WHERE usr_id = :uid AND gui_id = :gid",
			values={
				"uid": member.id,
				"gid": member.guild.id
			}
		)

		if row:
			info = MemberInfo(member)
			info.exp = row['mem_exp']
			info.credits = row['mem_credits']
			info.description = row['mem_description']
			return info

		return None

	async def get_member_info(self, member):
		info = await self.fetch_member_info(member)

		if info:
			return info

		settings = await self._bot.guildsettings.get_settings(member.guild)
		
		return MemberInfo(
			member, 
			credits=settings['prog_credits_initial_amount'] if 'prog_credits_initial_amount' in settings else 0
		)

	async def update_member_info(self, memberinfo, assume_exists=False):
		conn = await self.get_database_connection()

		if not assume_exists:
			existinginfo = await self.fetch_member_info(memberinfo.member)

			if not existinginfo:
				async with conn.transaction():
					await conn.execute(
						query="INSERT INTO member VALUES (:uid, :gid, :exp, :credits, :description)",
						values={
							"uid": memberinfo.member.id,
							"gid": memberinfo.member.guild.id,
							"exp": memberinfo.exp,
							"credits": memberinfo.credits,
							"description": memberinfo.description
						}
					)

				return

		async with conn.transaction():
			await conn.execute(
				query="UPDATE member SET mem_exp = :exp, mem_credits = :credits, mem_description = :description WHERE usr_id = :uid AND gui_id = :gid",
				values={
					"uid": memberinfo.member.id,
					"gid": memberinfo.member.guild.id,
					"exp": memberinfo.exp,
					"credits": memberinfo.credits,
					"description": memberinfo.description
				}
			)

	def block_member_changes(self, memberinfo):
		if memberinfo.member.guild.id in self._blocked:
			self._blocked[memberinfo.member.guild.id].append(memberinfo.member.id)
		else:
			self._blocked[memberinfo.member.guild.id] = [memberinfo.member.id]

	def is_member_changes_blocked(self, memberinfo):
		return memberinfo.member.guild.id in self._blocked and memberinfo.member.id in self._blocked[memberinfo.member.guild.id]

	def unblock_member_changes(self, memberinfo):
		if memberinfo.member.guild.id in self._blocked:
			try:
				self._blocked[memberinfo.member.guild.id].remove(memberinfo.member.id)

				if not self._blocked[memberinfo.member.guild.id]:
					del self._blocked[memberinfo.member.guild.id]
			except ValueError:
				pass

	async def on_member_levelup(self, member):
		for callback in self._levelup_listeners:
			await callback(self._bot, self, member)
		
	def add_levelup_callback(self, callback):
		if callback in self._levelup_listeners:
			return

		self._levelup_listeners.append(callback)

	def remove_levelup_callback(self, callback):
		try:
			self._levelup_listeners.remove(callback)
		except ValueError:
			pass