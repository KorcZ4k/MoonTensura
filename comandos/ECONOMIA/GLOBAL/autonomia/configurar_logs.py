import discord
from discord.ext import commands
from .logs_economicos import PublicadorLogsEconomicos


class ConfigurarLogsEconomicos(commands.Cog):
    """Configuração dos canais oficiais de acontecimentos da Economia Global."""

    CANAIS_PADRAO = {
        "rotas_comerciais": 1545198413472071841,
        "tratados_empresariais": 1545198304604983386,
        "anuncios_governamentais": 1545198192876978247,
        "crises_financeiras": 1545198066406006844,
        "empresas": 1545197844372258836,
    }

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.logs = PublicadorLogsEconomicos(self.db)

    @commands.command(name="configurar_logs_economia", aliases=["logs_economia"])
    @commands.has_permissions(administrator=True)
    async def configurar_logs_economia(self, ctx):
        """Registra os canais oficiais de logs da economia global neste servidor."""
        documento = self.logs.registrar_canais(ctx.guild.id, self.CANAIS_PADRAO)
        embed = discord.Embed(
            title="📡 Canais da Economia Global configurados",
            description="Os acontecimentos econômicos serão publicados automaticamente nos canais correspondentes.",
            color=discord.Color.green(),
        )
        nomes = {
            "rotas_comerciais": "💰 Rotas Comerciais",
            "tratados_empresariais": "📜 Tratados Empresariais",
            "anuncios_governamentais": "📢 Anúncios Governamentais",
            "crises_financeiras": "📉 Crises Financeiras",
            "empresas": "🏢 Empresas",
        }
        for chave, nome in nomes.items():
            embed.add_field(name=nome, value=f"<#{documento['canais'][chave]}>", inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ConfigurarLogsEconomicos(bot))
