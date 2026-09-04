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
        

    @commands.command(name="sistemas")
    @commands.has_permissions(administrator= True)
    async def sistema(self, ctx):
        sys = discord.Embed(
            title = "Tensura Moon",
            description = """""",
            color = "",
            timestamp = horario
        )
        sys.set_footer = "Tensura Moon - Korczak Technologies!"
        sys.set_thumbnail(ctx.guild.avatar.url)
        sys.set_image(url = '')

        await ctx.send(embed=sys)
        


async def setup(bot):
    await bot.add_cog(Loritta(bot))