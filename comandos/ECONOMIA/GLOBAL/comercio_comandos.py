import discord
from discord.ext import commands
from database.python.mongodb import db
from .motor import MotorEconomiaGlobal
from .comercio_internacional import MotorComercioInternacional


class ComercioInternacional(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.motor = MotorEconomiaGlobal(db)
        self.comercio = MotorComercioInternacional(db, self.motor)

    @commands.command(name="configurar_rota")
    @commands.has_permissions(administrator=True)
    async def configurar_rota(self, ctx, origem: str, destino: str, modelo: str = "tradicional", distancia: float = 1, tarifa: float = 0, risco: float = 0):
        r = self.comercio.configurar_rota(origem, destino, modelo, distancia, tarifa, risco)
        if "erro" in r:
            await ctx.send(embed=discord.Embed(title="❌ Rota", description="Modelo inválido.", color=discord.Color.red())); return
        e = discord.Embed(title="🛣️ Rota Comercial Configurada", color=discord.Color.green())
        e.add_field(name="Origem", value=origem); e.add_field(name="Destino", value=destino); e.add_field(name="Modelo", value=modelo)
        e.add_field(name="Custo Logístico Base", value=f"{r['custo_logistico_base'] * 100:.0f}%")
        await ctx.send(embed=e)

    @commands.command(name="cambio")
    async def cambio(self, ctx, valor: float, origem: str, destino: str):
        r = self.comercio.converter(valor, origem, destino)
        if "erro" in r:
            await ctx.send(embed=discord.Embed(title="❌ Câmbio", description="Moeda não configurada.", color=discord.Color.red())); return
        await ctx.send(embed=discord.Embed(title="💱 Conversão", description=f"**{valor:,.2f} {origem.upper()}** → **{r['valor']:,.2f} {destino.upper()}**\nEquivalente: **{self.motor.formatar_moeda(r['bronze_equivalente'])}**", color=discord.Color.blue()))

    @commands.command(name="balanca_comercial", aliases=["balanca"])
    async def balanca(self, ctx, governo: str):
        r = self.comercio.balanca_comercial(governo)
        e = discord.Embed(title=f"🌐 Balança Comercial — {governo}", color=discord.Color.gold())
        e.add_field(name="Exportações", value=self.motor.formatar_moeda(r['exportacoes_bronze']))
        e.add_field(name="Importações", value=self.motor.formatar_moeda(r['importacoes_bronze']))
        e.add_field(name="Saldo", value=self.motor.formatar_moeda(abs(r['saldo_bronze'])))
        e.add_field(name="Situação", value=r['situacao'].capitalize())
        await ctx.send(embed=e)


async def setup(bot):
    await bot.add_cog(ComercioInternacional(bot))
