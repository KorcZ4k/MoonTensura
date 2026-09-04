import discord
from discord.ext import commands

from database.python.mongodb import db
from database.python.Hunos import economia_hunos
from database.python.moeda_hunos import formatar_hunos


class PaineisEconomicos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.empresas = db["Economia_Empresas"]
        self.governos = db["Economia_Governos"]
        self.tesouros = db["Economia_Tesouros"]
        self.relatorios = db["Economia_Relatorios"]

    @commands.command(name="painel_economia", aliases=["painel_economico"])
    async def painel_economia(self, ctx):
        hunos = economia_hunos(ctx.guild.id)
        empresas = self.empresas.count_documents({"guild_id": str(ctx.guild.id)})
        ativas = self.empresas.count_documents({"guild_id": str(ctx.guild.id), "status": {"$ne": "falida"}})
        governo = self.governos.find_one({"governo_id": str(ctx.guild.id)})
        tesouro = self.tesouros.find_one({"governo_id": str(ctx.guild.id)}) or {}

        embed = discord.Embed(title="📊 Painel Econômico", color=discord.Color.blue())
        embed.add_field(name="💰 Hunos em circulação", value=formatar_hunos(hunos.get("total", 0)), inline=False)
        embed.add_field(name="👥 Participantes", value=str(hunos.get("jogadores", 0)), inline=True)
        embed.add_field(name="🏢 Empresas", value=f"{ativas}/{empresas} ativas", inline=True)
        if governo:
            embed.add_field(name="🏛️ Governo", value=governo.get("nome", "Governo"), inline=True)
            embed.add_field(name="🏦 Tesouro", value=formatar_hunos(tesouro.get("saldo_bronze", 0)), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="ranking_empresas")
    async def ranking_empresas(self, ctx):
        empresas = list(self.empresas.find({"guild_id": str(ctx.guild.id), "status": {"$ne": "falida"}}))
        empresas.sort(key=lambda e: float(e.get("caixa_bronze", e.get("capital", 0)) or 0), reverse=True)
        if not empresas:
            await ctx.send("📭 Ainda não existem empresas para classificar.")
            return
        linhas = []
        for posicao, empresa in enumerate(empresas[:10], 1):
            valor = empresa.get("caixa_bronze", empresa.get("capital", 0))
            linhas.append(f"**{posicao}. {empresa.get('nome', 'Sem nome')}** — {formatar_hunos(valor)}")
        await ctx.send(embed=discord.Embed(title="🏢 Ranking de Empresas", description="\n".join(linhas), color=discord.Color.gold()))

    @commands.command(name="ranking_governos")
    async def ranking_governos(self, ctx):
        governos = list(self.governos.find())
        dados = []
        for governo in governos:
            tesouro = self.tesouros.find_one({"governo_id": str(governo.get("governo_id"))}) or {}
            dados.append((governo, float(tesouro.get("saldo_bronze", 0) or 0)))
        dados.sort(key=lambda item: item[1], reverse=True)
        if not dados:
            await ctx.send("📭 Ainda não existem governos para classificar.")
            return
        linhas = [f"**{i}. {g.get('nome', 'Governo')}** — {formatar_hunos(valor)}" for i, (g, valor) in enumerate(dados[:10], 1)]
        await ctx.send(embed=discord.Embed(title="🏛️ Ranking de Governos", description="\n".join(linhas), color=discord.Color.purple()))

    @commands.command(name="relatorio_economia")
    async def relatorio_economia(self, ctx):
        relatorio = self.relatorios.find_one({"tipo": "global"}, sort=[("data", -1)])
        if not relatorio:
            await ctx.send("📭 Ainda não existe um relatório global. Aguarde um ciclo econômico.")
            return
        macro = relatorio.get("macro", {})
        empresas = relatorio.get("empresas", {})
        classificacao = relatorio.get("classificacao", {})
        embed = discord.Embed(title="📈 Relatório da Economia", color=discord.Color.teal())
        embed.add_field(name="Estado", value=f"{classificacao.get('estado', 'indisponível').title()}\nSaúde: {float(classificacao.get('indice_saude', 0)):.1f}/100", inline=True)
        embed.add_field(name="Preços", value=f"Índice: {float(macro.get('indice_precos', 0)):.2f}\nJuros: {float(macro.get('taxa_juros', 0))*100:.2f}%", inline=True)
        embed.add_field(name="Empresas", value=f"Ativas: {empresas.get('ativas', 0)}\nFalidas: {empresas.get('falidas', 0)}", inline=True)
        embed.add_field(name="Receita empresarial", value=formatar_hunos(empresas.get("receita_bronze", 0)), inline=False)
        embed.add_field(name="Lucro empresarial", value=formatar_hunos(max(0, empresas.get("lucro_bronze", 0))), inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(PaineisEconomicos(bot))
