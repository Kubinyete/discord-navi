import discord
import math
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
    previous_level = meminfo.get_current_level()

    calc = len(message.content) / expected_message_length
    meminfo.exp += math.floor(exp_reward if calc >= 1 else calc * exp_reward)

    await pm.update_member_info(meminfo)

    current_level = meminfo.get_current_level()
    if current_level > previous_level and show_levelup:
        embeditem = EmbedItem(
            description=f"**{meminfo.member.name}** acabou de alcançar o nível **{current_level}**",
            color=discord.Colour.green()
        )

        await bot.feedback(message, feedback=None, embeditem=embeditem)

async def callbackCreateProgressionManagerInstance(bot):
    ProgressionManager.get_instance(bot)

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