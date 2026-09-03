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

    @commands.command(name="configurar_rota_comercial", aliases=["rota_comercial"])
    @commands.has_permissions(administrator=True)
    async def configurar_rota(self, ctx, origem: str, destino: str, modelo: str = "tradicional", distancia: float = 1, tarifa: float = 0, risco: float = 0):
        r = self.comercio.configurar_rota(origem, destino, modelo, distancia, tarifa, risco)
        if "erro" in r:
            await ctx.send(embed=discord.Embed(title="❌ Rota", description="Modelo inválido.", color=discord.Color.red()))
            return
        e = discord.Embed(title="🛣️ Rota Comercial Configurada", color=discord.Color.green())
        e.add_field(name="Origem", value=origem)
        e.add_field(name="Destino", value=destino)
        e.add_field(name="Modelo", value=modelo)
        e.add_field(name="Custo Logístico Base", value=f"{r['custo_logistico_base'] * 100:.0f}%")
        await ctx.send(embed=e)

    @commands.command(name="registrar_governo_economia")
    @commands.has_permissions(administrator=True)
    async def registrar_governo_economia(self, ctx, governo: str, reservas: float = 0, moeda: str = "BRONZE"):
        r = self.comercio.registrar_governo(governo, governo, reservas, moeda)
        await ctx.send(embed=discord.Embed(title="🏛️ Governo Econômico Registrado", description=f"**{r['nome']}**\nReservas: **{self.motor.formatar_moeda(r['reservas_internacionais_bronze'])}**\nMoeda: **{r['moeda']}**", color=discord.Color.green()))

    @commands.command(name="acordo_comercial")
    @commands.has_permissions(administrator=True)
    async def acordo_comercial(self, ctx, origem: str, destino: str, nome: str, reducao_tarifa: float = 0, livre_comercio: bool = False):
        r = self.comercio.criar_acordo(origem, destino, nome, reducao_tarifa, livre_comercio)
        descricao = "Livre comércio total" if r['livre_comercio'] else f"Redução tarifária: {r['reducao_tarifa'] * 100:.1f}%"
        await ctx.send(embed=discord.Embed(title="🤝 Acordo Comercial", description=f"**{origem} ↔ {destino}**\n{descricao}\nNome: **{r['nome']}**", color=discord.Color.blue()))

    @commands.command(name="definir_cambio")
    @commands.has_permissions(administrator=True)
    async def definir_cambio(self, ctx, moeda: str, bronze_por_unidade: float, governo: str = None):
        r = self.comercio.definir_cambio(moeda, bronze_por_unidade, governo)
        await ctx.send(embed=discord.Embed(title="💱 Câmbio Atualizado", description=f"**1 {r['moeda']} = {r['bronze_por_unidade']:,.4f} Bronze**", color=discord.Color.gold()))

    @commands.command(name="cambio_comercial")
    async def cambio(self, ctx, valor: float, origem: str, destino: str):
        r = self.comercio.converter(valor, origem, destino)
        if "erro" in r:
            await ctx.send(embed=discord.Embed(title="❌ Câmbio", description="Moeda não configurada.", color=discord.Color.red()))
            return
        await ctx.send(embed=discord.Embed(title="💱 Conversão", description=f"**{valor:,.2f} {origem.upper()}** → **{r['valor']:,.2f} {destino.upper()}**\nEquivalente: **{self.motor.formatar_moeda(r['bronze_equivalente'])}**", color=discord.Color.blue()))

    @commands.command(name="balanca_comercial_global", aliases=["balanca_global"])
    async def balanca(self, ctx, governo: str):
        r = self.comercio.balanca_comercial(governo)
        e = discord.Embed(title=f"🌐 Balança Comercial — {governo}", color=discord.Color.gold())
        e.add_field(name="Exportações", value=self.motor.formatar_moeda(r['exportacoes_bronze']))
        e.add_field(name="Importações", value=self.motor.formatar_moeda(r['importacoes_bronze']))
        e.add_field(name="Saldo", value=self.motor.formatar_moeda(abs(r['saldo_bronze'])))
        e.add_field(name="Reservas Internacionais", value=self.motor.formatar_moeda(r['reservas_internacionais_bronze']))
        e.add_field(name="Situação", value=r['situacao'].capitalize())
        await ctx.send(embed=e)


async def setup(bot):
    await bot.add_cog(ComercioInternacional(bot))
