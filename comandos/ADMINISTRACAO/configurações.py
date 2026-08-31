import asyncio
import discord
from database.python.mongodb import db
from discord.ext import commands
import datetime

fuso = datetime.timezone(datetime.timedelta(hours = -3))
horario = datetime.datetime.now(fuso)

class Loritta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name = "clear", aliases = ['limpar'])
    @commands.has_permissions(manage_messages = True)
    async def clear(self, ctx, quantidade: int = 10):
        
        mensagens_deletadas = await ctx.channel.purge(limit = quantidade)
        
        embedd = discord.Embed(
            title = 'Limpar Mensagens',
            color = 0xff0000,
            description = f'**Foram limpadas {quantidade} mensagens do chat**',
            timestamp = horario,
        )
        embedd.set_footer(
            text = "Moon Tensura - Korczak Technologies!"
        )
        await asyncio.sleep(1)
        await ctx.send(embed=embedd)

async def setup(bot):
    await bot.add_cog(Loritta(bot))