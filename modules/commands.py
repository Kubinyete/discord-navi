import discord
import navibot

# @SECTION
# Comandos disponibilizados por padrão pelo bot

async def command_helloworld(bot, message, args, flags, handler):
    await bot.feedback(message, feedback=navibot.SUCCESS, title="Hello world!", text="Olá mundo!")

async def command_help(bot, message, args, flags, handler):
	if len(args) < 2:
		helptext = "**Comandos disponíveis**\n\n"

		for key in bot.commands.getCommands().keys():
			helptext = helptext + "`{}`\n{}\n\n".format(bot.commands.get(key).name, bot.commands.get(key).description)
	else:
		handler = bot.commands.get(args[1])

		if handler:
			helptext = "**{}**\n`Uso: {}`\n\n{}".format(handler.name, handler.usage, handler.description)
		else:
			await bot.feedback(message, feedback=navibot.WARNING, text="O comando '{}' não existe".format(args[1]))
			return

	await bot.feedback(message, feedback=navibot.SUCCESS, text=helptext)

async def command_embed(bot, message, args, flags, handler):
	if len(args) < 2 and (not "title" in flags and not "img" in flags):
		await bot.feedback(message, navibot.COMMAND_INFO, text=handler.usage)
		return

	title = ""
	description = ""
	image = ""

	if len(args) > 1:
		description = " ".join(args[1:])

	if "title" in flags:
		title = flags["title"]

	if "img" in flags:
		image = flags["img"]

	embed = discord.Embed(title=title, description=description, color=discord.Colour.purple())
	embed.set_image(url=image)
	embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

	await message.channel.send(embed=embed)
	await bot.feedback(message, navibot.SUCCESS)

async def command_avatar(bot, message, args, flags, handler):
	if len(message.mentions) != 1:
		await bot.feedback(message, navibot.COMMAND_INFO, text=handler.usage)
		return

	user = message.mentions[0]

	embed = discord.Embed(title="Avatar de {}".format(user.name), color=discord.Colour.purple())
	embed.set_image(url=user.avatar_url_as(size=256))
	embed.set_footer(text=message.author.name, icon_url=message.author.avatar_url_as(size=32))

	await message.channel.send(embed=embed)
	await bot.feedback(message, navibot.SUCCESS)