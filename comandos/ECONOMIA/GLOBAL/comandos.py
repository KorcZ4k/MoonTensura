import discord
from discord.ext import commands, tasks
from database.python.mongodb import db
from .motor import MotorEconomiaGlobal
from .producao import MotorProducao


class EconomiaGlobal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.motor = MotorEconomiaGlobal(db)
        self.producao = MotorProducao(db, self.motor)
        self.ciclo_economico.start()

    def cog_unload(self):
        self.ciclo_economico.cancel()

    @tasks.loop(minutes=1)
    async def ciclo_economico(self):
        resultado = self.motor.ciclo_economico()
        estado = resultado.get("estado", {})
        print(f"🌐 Ciclo econômico: índice={estado.get('indice_precos', 0):.4f} | reposição={resultado.get('reposicoes', 0)}")

    @ciclo_economico.before_loop
    async def antes_ciclo(self):
        await self.bot.wait_until_ready()

    @commands.command(name="configurar_mercado", aliases=["configmercado"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def configurar_mercado(self, ctx, tipo: str, categoria: str = "comum"):
        try:
            self.motor.configurar_mercado(ctx.guild.id, ctx.channel.id, tipo.lower(), categoria.lower())
        except ValueError as erro:
            await ctx.send(embed=discord.Embed(title="❌ Configuração inválida", description=str(erro), color=discord.Color.red()))
            return
        await ctx.send(embed=discord.Embed(title="🏪 Mercado configurado", description=f"Canal: {ctx.channel.mention}\nTipo: **{tipo.capitalize()} ({categoria})**", color=discord.Color.green()))

    @commands.command(name="repor_estoque")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def repor_estoque(self, ctx, produto_id: str, quantidade: int = None):
        resultado = self.producao.repor_mercado(ctx.guild.id, ctx.channel.id, produto_id, quantidade)
        if "erro" in resultado:
            await ctx.send(f"❌ Reposição não realizada: `{resultado['erro']}`")
            return
        custo = resultado["custo"]
        embed = discord.Embed(title="🏭 Estoque produzido", color=discord.Color.green())
        embed.add_field(name="Quantidade", value=str(resultado["quantidade"]), inline=True)
        embed.add_field(name="Custo total", value=self.motor.formatar_moeda(custo["total"]), inline=True)
        embed.add_field(name="Salários", value=self.motor.formatar_moeda(custo["salarios"]), inline=True)
        embed.add_field(name="Insumos", value=self.motor.formatar_moeda(custo["insumos"]), inline=True)
        embed.add_field(name="Energia", value=self.motor.formatar_moeda(custo["energia"]), inline=True)
        embed.add_field(name="Logística", value=self.motor.formatar_moeda(custo["logistica"]), inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="mercado")
    @commands.guild_only()
    async def mercado(self, ctx):
        mercado = self.motor.mercado_do_canal(ctx.guild.id, ctx.channel.id)
        if not mercado:
            await ctx.send("❌ Este canal ainda não é um mercado configurado.")
            return
        receitas = float(mercado.get("receita_bronze", 0))
        custos = float(mercado.get("custos_operacionais_bronze", 0))
        embed = discord.Embed(title="📊 Mercado Local", color=discord.Color.gold())
        embed.add_field(name="Tipo", value=f"{mercado['tipo'].capitalize()} — {mercado.get('categoria', 'comum')}")
        embed.add_field(name="Demanda", value=str(round(mercado.get("demanda", 0), 2)))
        embed.add_field(name="Oferta", value=str(round(mercado.get("oferta", 0), 2)))
        embed.add_field(name="Receitas", value=self.motor.formatar_moeda(receitas))
        embed.add_field(name="Custos", value=self.motor.formatar_moeda(custos))
        embed.add_field(name="Resultado", value=self.motor.formatar_moeda(receitas - custos))
        await ctx.send(embed=embed)

    @commands.command(name="economia_global", aliases=["eco_global", "macroeconomia"])
    async def economia_global(self, ctx):
        dados = self.motor.relatorio_global()
        embed = discord.Embed(title="🌐 Economia Global de Tensura", color=discord.Color.blue())
        embed.add_field(name="Índice de preços", value=f"{float(dados.get('indice_precos', 100.0)):.4f}")
        embed.add_field(name="Inflação por minuto", value=f"{float(dados.get('inflacao_minuto', 0.0)) * 100:+.4f}%")
        embed.add_field(name="Liquidez internacional", value=f"{dados.get('liquidez_ouro', 0):,.2f} ouro")
        embed.add_field(name="Fluxo de capitais", value=self.motor.formatar_moeda(dados.get('fluxo_capital', 0)), inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(EconomiaGlobal(bot))
