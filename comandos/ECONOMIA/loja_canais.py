import discord
from discord.ext import commands
from database.python.mongodb import db


CONFIG = db["configuracoes_servidor"]


class LojaCanais(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_check(self._verificar_canal_loja)

    async def cog_unload(self):
        try:
            self.bot.remove_check(self._verificar_canal_loja)
        except ValueError:
            pass

    async def _verificar_canal_loja(self, ctx):
        command = ctx.command
        if command is None:
            return True

        # Restringe o grupo !loja e todos os seus subcomandos.
        if command.name != "loja" and command.qualified_name != "loja":
            if not command.qualified_name.startswith("loja "):
                return True

        if ctx.guild is None:
            raise commands.NoPrivateMessage()

        config = CONFIG.find_one({"guild_id": ctx.guild.id}) or {}
        canais_loja = config.get("canais_loja", [])

        if ctx.channel.id not in canais_loja:
            raise commands.CheckFailure(
                "Este comando só pode ser usado em um canal de RP da loja."
            )

        return True

    @commands.command(name="adc_loja", aliases=["add_loja", "adicionar_loja"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def adc_loja(self, ctx, channel: discord.TextChannel = None):
        """Adiciona um canal à lista de canais permitidos para a loja."""
        channel = channel or ctx.channel

        resultado = CONFIG.update_one(
            {"guild_id": ctx.guild.id},
            {"$addToSet": {"canais_loja": channel.id}},
            upsert=True
        )

        if resultado.modified_count == 0:
            descricao = f"{channel.mention} já estava configurado como canal de RP da loja."
            cor = discord.Color.orange()
        else:
            descricao = f"{channel.mention} foi adicionado aos canais de RP da loja."
            cor = discord.Color.green()

        embed = discord.Embed(
            title="🏪 Canal de Loja Configurado",
            description=descricao,
            color=cor
        )
        embed.add_field(
            name="Comandos liberados",
            value="`!loja` e todos os seus subcomandos, incluindo `comprar`, `usar`, `inventario` e `categoria`.",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(name="rmv_loja", aliases=["remover_loja", "del_loja"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def rmv_loja(self, ctx, channel: discord.TextChannel = None):
        """Remove um canal da lista de canais permitidos para a loja."""
        channel = channel or ctx.channel

        resultado = CONFIG.update_one(
            {"guild_id": ctx.guild.id},
            {"$pull": {"canais_loja": channel.id}},
            upsert=True
        )

        if resultado.modified_count == 0:
            descricao = f"{channel.mention} não estava configurado como canal de RP da loja."
            cor = discord.Color.orange()
        else:
            descricao = f"{channel.mention} foi removido dos canais de RP da loja."
            cor = discord.Color.red()

        await ctx.send(embed=discord.Embed(
            title="🏪 Canal de Loja Atualizado",
            description=descricao,
            color=cor
        ))

    @commands.command(name="canais_loja", aliases=["lista_loja"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def canais_loja(self, ctx):
        """Lista os canais permitidos para os comandos da loja."""
        config = CONFIG.find_one({"guild_id": ctx.guild.id}) or {}
        canais_ids = config.get("canais_loja", [])
        canais = []

        for channel_id in canais_ids:
            channel = ctx.guild.get_channel(channel_id)
            if channel is not None:
                canais.append(channel.mention)

        await ctx.send(embed=discord.Embed(
            title="🏪 Canais de RP da Loja",
            description="\n".join(canais) if canais else "Nenhum canal configurado.",
            color=discord.Color.gold()
        ))

    @adc_loja.error
    @rmv_loja.error
    @canais_loja.error
    async def admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=discord.Embed(
                title="❌ Sem permissão",
                description="Apenas administradores podem configurar os canais da loja.",
                color=discord.Color.red()
            ))
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Canal inválido. Mencione um canal válido.")
        else:
            raise error

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure) and ctx.command:
            command = ctx.command
            if command.name == "loja" or command.qualified_name.startswith("loja "):
                await ctx.send(embed=discord.Embed(
                    title="🏪 Canal não permitido",
                    description="Os comandos da loja só podem ser usados nos canais de RP da loja configurados pela administração.",
                    color=discord.Color.red()
                ))


async def setup(bot):
    await bot.add_cog(LojaCanais(bot))
