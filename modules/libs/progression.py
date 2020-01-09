class MemberInfo:
	def __init__(self, member, **kwargs):
		self.member = member
		self.exp = kwargs.get('exp', 0)
		self.credits = kwargs.get('credits', 0)

class ProgressionManager:
	def __init__(self, bot):
		self._bot = bot

	async def get_database_connection(self):
		return await self._bot.get_database_connection()

	@staticmethod
	def get_level(exp):
		pass

	async def fetch_member_info(self, member):
		conn = await self.get_database_connection()

		row = await conn.fetch_one(
			query="SELECT usr_exp, usr_credits FROM member WHERE usr_id = :uid AND gui_id = :gid",
			values={
				"uid": member.id,
				"gid": member.guild.id
			}
		)

		if row:
			info = MemberInfo(member)
			info.exp = row['mem_exp']
			info.creditos = row['mem_credits']
			return info

		return None

	async def get_member_info(self, member):
		info = self.fetch_member_info(member)

		if info:
			return info

		return MemberInfo(member)

	async def update_member_info(self, memberinfo, assume_exists=False):
		conn = await self.get_database_connection()

		if not assume_exists:
			existinginfo = self.fetch_member_info(memberinfo.member)

			if not existinginfo:
				async with conn.transaction():
					await conn.execute(
						query="INSERT INTO member VALUES (:uid, :gid, :exp, :credits)",
						values={
							"uid": memberinfo.member.id,
							"gid": memberinfo.member.guild.id,
							"exp": memberinfo.exp,
							"credits": memberinfo.credits
						}
					)

				return

		async with conn.transaction():
			await conn.execute(
				query="UPDATE member SET mem_exp = :exp, mem_credits = :credits WHERE usr_id = :uid AND gui_id = :gid",
				values={
					"uid": memberinfo.member.id,
					"gid": memberinfo.member.guild.id,
					"exp": memberinfo.exp,
					"credits": memberinfo.credits
				}
			)
		