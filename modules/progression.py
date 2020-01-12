import discord
import math
import asyncio
from naviclient import NaviCallback
from navibot import EmbedSlide
from navibot import EmbedItem
from modules.libs.progression import ProgressionManager

async def callbackProgressionOnMessage(bot, message):
	if message.author == bot.client.user or message.author.bot or message.content.startswith(bot.prefix):
		return

	settings = await bot.guildsettings.get_settings(message.guild)

	expected_message_length = settings['prog_expected_message_length'] if 'prog_expected_message_length' in settings else 1
	exp_reward = settings['prog_message_reward'] if 'prog_message_reward' in settings else 25
	show_levelup = settings['prog_show_levelup_message'] if 'prog_show_levelup_message' in settings else False

	pm = ProgressionManager.get_instance()

	meminfo = await pm.get_member_info(message.author)
	blocked_once = False

	while pm.is_member_changes_blocked(meminfo):
		# Tente novamente em 200ms
		await asyncio.sleep(.200)
		blocked_once = True

	pm.block_member_changes(meminfo)

	if blocked_once:
		# Fomos bloqueados alguma vez, pegue a informação novamente.
		meminfo = await pm.get_member_info(message.author)

	previous_level = meminfo.get_current_level()
	calc = len(message.content) / expected_message_length
	meminfo.exp += math.floor(exp_reward if calc >= 1 else calc * exp_reward)
	current_level = meminfo.get_current_level()
	
	previous_credits = meminfo.credits
	await pm.on_member_levelup(meminfo)

	if current_level > previous_level:
		if show_levelup:
			description = f"**{meminfo.member.name}** acabou de alcançar o nível **{current_level}**"

			if meminfo.credits > previous_credits:
				description += f"\n+ **{meminfo.credits - previous_credits}** créditos adquiridos"

			embeditem = EmbedItem(
				description=description,
				color=discord.Colour.green()
			)

			await bot.feedback(message, feedback=None, embeditem=embeditem)

	await pm.update_member_info(meminfo)
	pm.unblock_member_changes(meminfo)

async def callbackOnLevelupCreditsReward(bot, pminstance, memberinfo):
	settings = await bot.guildsettings.get_settings(memberinfo.member.guild)

	multiplier = settings['prog_levelup_credits_multiplier'] if 'prog_levelup_credits_multiplier' in settings else 0.4
	base = settings['prog_levelup_credits_base'] if 'prog_levelup_credits_base' in settings else 100

	credits_amount = int(memberinfo.get_current_level() * base * multiplier)

	memberinfo.credits += credits_amount

async def callbackCreateProgressionManagerInstance(bot):
	pm = ProgressionManager.get_instance(bot)

	pm.add_levelup_callback(callbackOnLevelupCreditsReward)

async def command_profile(bot, message, args, flags, handler):
	pm = ProgressionManager.get_instance()

	memberinfo = await pm.get_member_info(message.author if len(message.mentions) == 0 else message.mentions[0])

	# @TODO:
	# Permitir visualizar um outro perfil a partir de uma menção

	items = [
		EmbedItem(
			description=memberinfo.description if memberinfo.description else "Nenhuma descrição está disponível",
			title=f"Perfil de {memberinfo.member.name}",
			footer=(memberinfo.member.name, memberinfo.member.avatar_url_as(size=32)),
			thumbnail=memberinfo.member.avatar_url_as(size=256),
			fields=[
				("Nivel", f"**{memberinfo.get_current_level()}**", True),
				("Créditos", f"**{memberinfo.credits}**", True),
				("Progresso", f"*+{memberinfo.get_exp_required()} EXP para alcançar o próximo nível*", False)
			]
		)
	]

	await EmbedSlide(items, message).send_and_wait(bot)

LISTEN={
	"on_ready": [
		callbackCreateProgressionManagerInstance
	],
	"on_message": [
		callbackProgressionOnMessage
	]
}