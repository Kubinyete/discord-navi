
class Character:
	def __init__(self, 
		id, 
		name_first, 
		name_last, 
		name_full, 
		name_native,
		image_large,
		image_medium,
		description,
		favourites
	):
		self.id = id
		self.name_first = name_first
		self.name_last = name_last
		self.name_full = name_full
		self.name_native = name_native
		self.image_large = image_large
		self.image_medium = image_medium
		self.description = description
		self.favourites = favourites

	def get_description(self):
		if self.description and len(self.description) > 0:
			spoiler = False
			ignore_next = False
			fdes = ""

			for i in range(len(self.description)):
				c = self.description[i]
				cnext = self.description[i + 1] if i + 1 < len(self.description) else ""

				if len(fdes) >= 2043:
					if spoiler:
						fdes += "...||"
					else:
						fdes += "..."

					break
				elif ignore_next:
					ignore_next = False
				elif c == "~" and cnext == "!" and not spoiler:
					spoiler = True
					ignore_next = True
					fdes += "||"
				elif c == "!" and cnext == "~" and spoiler:
					spoiler = False
					ignore_next = True
					fdes += "||"
				else:
					fdes += c

			return fdes
		else:
			return "Nenhuma descrição está disponível."

class Error(Exception):
	def __init__(self, message, status, locations):
		self.message = message
		self.status = status
		self.locations = locations

class ErrorCollection(Exception):
	def __init__(self, errors):
		self.errors = errors

class AniListApi:
	unique_instance = None

	def __init__(self, bot):
		self._bot = bot

	@staticmethod
	def get_instance(bot=None):
		if AniListApi.unique_instance is None and not bot is None:
			AniListApi.unique_instance = AniListApi(bot)
		
		return AniListApi.unique_instance

	async def send_request(self, query, variables={}):
		json = await self._bot.http.post_json("https://graphql.anilist.co", json={
			"query": query,
			"variables": variables
		})

		if 'errors' in json:
			raise ErrorCollection(
				[
					Error(
						error['message'],
						error['status'],
						[(l['line'], l['column']) for l in error['locations']]
					) for error in json['errors']
				]
			)
		
		return json

	async def search_characters(self, search, page=1, limit=20):
		ret = []

		data = await self.send_request("""
query ($search:String, $page:Int, $perpage:Int) {
	Page (page: $page, perPage: $perpage) {
		characters (search: $search, sort: SEARCH_MATCH) {
			id,
			name {
				first
				last
				full
				native
			},
			image {
				large
				medium
			},
			description,
			favourites
		}
	}
}
""", variables={
	"search": search, 
	"page": page, 
	"perpage": limit
})

		for character in data['data']['Page']['characters']:
			ret.append(Character(
				character['id'],
				character['name']['first'],
				character['name']['last'],
				character['name']['full'],
				character['name']['native'],
				character['image']['large'],
				character['image']['medium'],
				character['description'],
				character['favourites'],
			))

		return ret