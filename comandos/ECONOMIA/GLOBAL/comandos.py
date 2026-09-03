import discord
from discord.ext import commands, tasks
from database.python.mongodb import db
from .motor import MotorEconomiaGlobal


class EconomiaGlobal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.motor = MotorEconomiaGlobal(db)
        self.ciclo_economico.start()

    def cog_unload(self):
        self.ciclo_economico.cancel()

    @tasks.loop(minutes=1)
    async def ciclo_economico(self):
        self.motor.tick()

    @ciclo_economico.before_loop
    async def antes_ciclo(self):
        await self.bot.wait_until_ready()

    @commands.command(name="configurar_mercado", aliases=["configmercado"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def configurar_mercado(self, ctx, tipo: str, categoria: str = "comum"):
        """Define o canal atual como taverna, loja ou bazar."""
        tipo = tipo.lower()
        categoria = categoria.lower()
        try:
            self.motor.configurar_mercado(ctx.guild.id, ctx.channel.id, tipo, categoria)
        except ValueError as erro:
            await ctx.send(embed=discord.Embed(title="❌ Configuração inválida", description=str(erro), color=discord.Color.red()))
            return
        destinos = {
            "taverna": "Comidas, bebidas e hospedagem",
            "loja": "Itens e equipamentos",
            "bazar": "Roupas e comércio variado"
        }
        embed = discord.Embed(title="🏪 Mercado configurado", color=discord.Color.green())
        embed.add_field(name="Canal", value=ctx.channel.mention, inline=False)
        embed.add_field(name="Tipo", value=f"{tipo.capitalize()} ({categoria})", inline=True)
        embed.add_field(name="Comércio", value=destinos[tipo], inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="mercado")
    @commands.guild_only()
    async def mercado(self, ctx):
        mercado = self.motor.mercado_do_canal(ctx.guild.id, ctx.channel.id)
        if not mercado:
            await ctx.send("❌ Este canal ainda não é um mercado configurado.")
            return
        embed = discord.Embed(title="📊 Mercado Local", color=discord.Color.gold())
        embed.add_field(name="Tipo", value=f"{mercado['tipo'].capitalize()} — {mercado.get('categoria','comum')}")
        embed.add_field(name="Demanda recente", value=str(round(mercado.get('demanda', 0), 2)))
        embed.add_field(name="Oferta recente", value=str(round(mercado.get('oferta', 0), 2)))
        embed.add_field(name="Multiplicador", value=f"{mercado.get('multiplicador_preco', 1.0):.4f}x")
        await ctx.send(embed=embed)

    @commands.command(name="economia_global", aliases=["eco_global", "macroeconomia"])
    async def economia_global(self, ctx):
        dados = self.motor.relatorio_global()
        indice = float(dados.get("indice_precos", 100.0))
        inflacao = float(dados.get("inflacao_minuto", 0.0)) * 100
        embed = discord.Embed(title="🌐 Economia Global de Tensura", color=discord.Color.blue())
        embed.add_field(name="Índice de preços", value=f"{indice:.4f}")
        embed.add_field(name="Inflação por minuto", value=f"{inflacao:+.4f}%")
        embed.add_field(name="Liquidez internacional", value=f"{dados.get('liquidez_ouro', 0):,.2f} ouro")
        embed.add_field(name="Fluxo de capitais", value=self.motor.formatar_moeda(dados.get('fluxo_capital', 0)), inline=False)
        embed.add_field(name="Paridade", value="1 Bronze = $1 | 1 Prata = 100 Bronzes | 1 Ouro = 100 Pratas | 1 Ouro Estelar = 100 Ouros", inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(EconomiaGlobal(bot))
