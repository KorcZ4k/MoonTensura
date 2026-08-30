import asyncio
import os

import datetime
import discord

from database.python.users import cadastro
from dotenv import load_dotenv
from discord.ext import commands

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(
    command_prefix="!", 
    intents=intents, 
    case_insensitive = True)

@bot.event
async def on_member_join(member):
    cadastro(
        user_id = member.id,
        guild_id = member.guild.id
    )
    avatar = member.display_avatar
    MSG = discord.Embed(
        title = '🎉 Novo Membro!',
        description = f'**Bem-vindo(a) {member.mention}, se aconchegue no Tensura Moon!',
        color = 0x1bb500,
        thumbnail = avatar
    )
    MSG.set_footer( 
                Text = "Tensura Moon - Korczak Technologies! "
        )

@bot.event
async def on_message(message):
    if message.content.startswith('!'):
        await message.channel.send('Olá! Eu estou em manutenção agora')
    await bot.process_commands(message)
    
@bot.event
async def on_ready():
    fuso_horario = datetime.timezone(
        datetime.timedelta(
            hours = -3 
            )
        )
    agora = datetime.datetime.now(fuso_horario)
    canal = bot.get_channel(1543040912912031775)
    
    print(f"Bot conectado como {bot.user}")
    
    if canal is not None:

        embed = discord.Embed(
            title = "🟢 | Online",
            description = "Moon Tensura está online e pronto para o RPG",
            colour = 0x1caa00
            )
        embed.timestamp = agora
        embed.set_footer( 
            text = "Tensura Moon - Korczak Technologies!"
    )
        embed.set_image(
            url = "https://media.discordapp.net/attachments/1543063886939299962/1543433478698303538/ChatGPT_Image_29_de_ago._de_2026_18_39_01.png?ex=6a94d9f0&is=6a938870&hm=5b141470e3d4d538c901485d7140ca4ab34cc0307416a0866780e0b499d477ee&=&format=webp&quality=lossless&width=512&height=205"
        )
        embed.set_thumbnail(
            url = "https://images-ext-1.discordapp.net/external/j5-V2MwaKBAxY7K-MYenUED_J6Nwldmze46JyyboRNE/%3Fsize%3D2048/https/cdn.discordapp.com/avatars/1543048534280900609/9ba9969adb274a158a2199c952997fe4.png?format=webp&quality=lossless&width=384&height=384"
        )
        await canal.send(embed=embed)
# Cadastro:
        for guild in bot.guilds:
            membros = [
            member
            for member in guild.members
            if not member.bot
        ]

        quantidade = cadastro(membros)

        print(
            f"{guild.name}: {quantidade} usuários processados."
        )

async def carregar_extensoes():
    await bot.load_extension("comandos.RPG.status")
    await bot.load_extension("comandos.ECONOMIA.Hunos")
    await bot.load_extension("comandos.ECONOMIA.Mora")
    await bot.load_extension("comandos.ADMINISTRACAO.configurações")

TOKEN = os.getenv('Discord_Token')
async def main():
    async with bot:
        await carregar_extensoes()
        await bot.start(TOKEN)

asyncio.run(main())


