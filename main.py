import asyncio
import os

import datetime
import discord

from database.python.users import cadastro
from dotenv import load_dotenv
from discord.ext import commands
from database.python.mongodb import db
from database.python.Hunos import init_db_hunos

init_db_hunos(db)

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    case_insensitive=True
)


@bot.event
async def on_member_join(member):
    cadastro(
        user_id=member.id,
        guild_id=member.guild.id
    )


@bot.event
async def on_ready():
    fuso_horario = datetime.timezone(datetime.timedelta(hours=-3))
    agora = datetime.datetime.now(fuso_horario)
    canal = bot.get_channel(1543040912912031775)
    print(f"Bot conectado como {bot.user}")
    if canal is not None:
        embed = discord.Embed(
            title="🟢 | Online",
            description="Moon Tensura está online e pronto para o RPG",
            colour=0x1caa00,
            timestamp=agora
        )
        embed.set_footer(text="Tensura Moon - Korczak Technologies!")
        await canal.send(embed=embed)
    for guild in bot.guilds:
        membros = [member for member in guild.members if not member.bot]
        quantidade = cadastro(membros)
        print(f"{guild.name}: {quantidade} usuários processados.")


async def carregar_extensoes():
    await bot.load_extension("comandos.RPG.luta")
    await bot.load_extension("comandos.RPG.treino")
    await bot.load_extension("comandos.RPG.magias")
    await bot.load_extension("comandos.RPG.habs")
    await bot.load_extension("comandos.RPG.usarhab")
    await bot.load_extension("comandos.RPG.status")
    await bot.load_extension("comandos.RPG.nivel")
    await bot.load_extension("comandos.RPG.nascimento")
    await bot.load_extension("comandos.RPG.correcoes_luta")
    await bot.load_extension("comandos.RPG.status_habilidades")

    await bot.load_extension("comandos.ECONOMIA.cassino")
    await bot.load_extension("comandos.ECONOMIA.loja")
    await bot.load_extension("comandos.ECONOMIA.loja_canais")
    await bot.load_extension("comandos.ECONOMIA.Hunos")
    await bot.load_extension("comandos.ECONOMIA.Mora")
    await bot.load_extension("comandos.ECONOMIA.recompensas")
    await bot.load_extension("comandos.ECONOMIA.hunos_interacoes")
    await bot.load_extension("comandos.ECONOMIA.GLOBAL.comandos")

    await bot.load_extension("comandos.ADMINISTRACAO.autorole_commands")
    await bot.load_extension("comandos.ADMINISTRACAO.autorole")
    await bot.load_extension("comandos.ADMINISTRACAO.configurações")
    await bot.load_extension("comandos.ADMINISTRACAO.moderacao")
    await bot.load_extension("comandos.ADMINISTRACAO.automod")
    await bot.load_extension("comandos.ADMINISTRACAO.boas_vindas")
    await bot.load_extension("comandos.ADMINISTRACAO.logs")


TOKEN = os.getenv("DISCORD_TOKEN")


async def main():
    async with bot:
        await carregar_extensoes()
        await bot.start(TOKEN)


asyncio.run(main())
