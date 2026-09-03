import discord
from discord.ext import commands
from database.python.mongodb import db
from .motor import MotorEconomiaGlobal
from .financeiro_avancado import MotorFinanceiroAvancado


class BancoCentral(commands.Cog):
    """Política monetária, dívida pública e estabilidade do sistema financeiro."""

    def __init__(self, bot):
        self.bot = bot
        self.motor = MotorEconomiaGlobal(db)
        self.financeiro = MotorFinanceiroAvancado(db, self.motor)
        self.dividas = db["Economia_Divida_Publica"]
        self.operacoes = db["Economia_Operacoes_Banco_Central"]

    def _registrar_operacao(self, tipo, valor, guild_id=None, detalhes=None):
        self.operacoes.insert_one({"tipo": tipo, "valor_bronze": float(valor), "governo_id": str(guild_id) if guild_id else None, "detalhes": detalhes or {}})

    @commands.command(name="definir_juros", aliases=["taxa_juros", "juros"])
    @commands.has_permissions(administrator=True)
    async def definir_juros(self, ctx, percentual: float):
        if not 0 <= percentual <= 100:
            await ctx.send("❌ A taxa deve estar entre 0% e 100%."); return
        estado = self.motor.definir_taxa_juros(percentual / 100)
        self._registrar_operacao("alteracao_juros", 0, ctx.guild.id, {"taxa": percentual / 100})
        embed = discord.Embed(title="🏦 Política de Juros Atualizada", color=discord.Color.blue())
        embed.add_field(name="Taxa de juros", value=f"**{float(estado.get('taxa_juros', 0)) * 100:.2f}%**")
        embed.add_field(name="Efeito", value="Juros maiores restringem crédito; juros menores estimulam consumo e investimento.", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="injetar_liquidez", aliases=["emitir_moeda"])
    @commands.has_permissions(administrator=True)
    async def injetar_liquidez(self, ctx, valor_bronze: float):
        if valor_bronze <= 0: await ctx.send("❌ O valor precisa ser positivo."); return
        estado = self.motor.ajustar_liquidez(valor_bronze, "injecao")
        self._registrar_operacao("injecao_liquidez", valor_bronze, ctx.guild.id)
        embed = discord.Embed(title="💰 Liquidez Injetada", color=discord.Color.green())
        embed.add_field(name="Valor", value=self.motor.formatar_moeda(valor_bronze))
        embed.add_field(name="Reservas", value=self.motor.formatar_moeda(estado.get("reservas_monetarias_bronze", 0)))
        embed.add_field(name="Crédito", value=self.motor.formatar_moeda(estado.get("credito_disponivel_bronze", 0)))
        await ctx.send(embed=embed)

    @commands.command(name="retirar_liquidez", aliases=["contrair_moeda"])
    @commands.has_permissions(administrator=True)
    async def retirar_liquidez(self, ctx, valor_bronze: float):
        if valor_bronze <= 0: await ctx.send("❌ O valor precisa ser positivo."); return
        estado = self.motor.ajustar_liquidez(valor_bronze, "retirada")
        self._registrar_operacao("retirada_liquidez", valor_bronze, ctx.guild.id)
        await ctx.send(embed=discord.Embed(title="🏦 Liquidez Retirada", description=f"Reservas restantes: **{self.motor.formatar_moeda(estado.get('reservas_monetarias_bronze', 0))}**", color=discord.Color.orange()))

    @commands.command(name="emitir_divida", aliases=["divida_publica"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def emitir_divida(self, ctx, valor_bronze: float, juros_percentual: float, prazo_ciclos: int = 1440):
        if valor_bronze <= 0 or juros_percentual < 0 or prazo_ciclos <= 0:
            await ctx.send("❌ Valor, juros e prazo precisam ser positivos."); return
        doc = {"governo_id": str(ctx.guild.id), "principal_bronze": float(valor_bronze), "saldo_bronze": float(valor_bronze), "taxa_juros": juros_percentual / 100, "prazo_ciclos": int(prazo_ciclos), "ciclos_restantes": int(prazo_ciclos), "status": "aberta"}
        self.dividas.insert_one(doc)
        self._registrar_operacao("emissao_divida", valor_bronze, ctx.guild.id, {"juros": juros_percentual, "prazo": prazo_ciclos})
        await ctx.send(embed=discord.Embed(title="📜 Dívida Pública Emitida", description=f"Principal: **{self.motor.formatar_moeda(valor_bronze)}**\nTaxa: **{juros_percentual:.2f}%**\nPrazo: **{prazo_ciclos} ciclos**", color=discord.Color.gold()))

    @commands.command(name="amortizar_divida", aliases=["pagar_divida"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def amortizar_divida(self, ctx, valor_bronze: float):
        resultado = self.financeiro.amortizar_divida(ctx.guild.id, valor_bronze)
        if "erro" in resultado:
            await ctx.send("❌ O tesouro não possui saldo suficiente para essa amortização."); return
        await ctx.send(embed=discord.Embed(title="📉 Dívida Amortizada", description=f"Valor pago: **{self.motor.formatar_moeda(resultado['pago_bronze'])}**", color=discord.Color.green()))

    @commands.command(name="criar_banco")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def criar_banco(self, ctx, nome: str, reservas_bronze: float, depositos_bronze: float = None):
        banco = self.financeiro.criar_banco(ctx.guild.id, nome, reservas_bronze, depositos_bronze)
        await ctx.send(embed=discord.Embed(title="🏛️ Banco Criado", description=f"**{banco['nome']}**\nReservas: {self.motor.formatar_moeda(banco['reservas_bronze'])}\nDepósitos: {self.motor.formatar_moeda(banco['depositos_bronze'])}", color=discord.Color.blue()))

    @commands.command(name="rating_soberano", aliases=["rating"])
    @commands.guild_only()
    async def rating_soberano(self, ctx):
        dados = self.financeiro.rating_soberano(ctx.guild.id)
        embed = discord.Embed(title="⭐ Rating Soberano", color=discord.Color.gold())
        embed.add_field(name="Classificação", value=dados["rating"])
        embed.add_field(name="Score", value=f"{dados['score']:.2f}/100")
        embed.add_field(name="Prêmio de risco", value=f"{dados['premio_risco'] * 100:.2f}%")
        embed.add_field(name="Dívida aberta", value=self.motor.formatar_moeda(dados["divida_total_bronze"]))
        embed.add_field(name="Inadimplências", value=str(dados["inadimplencias"]))
        await ctx.send(embed=embed)

    @commands.command(name="estabilidade_bancaria", aliases=["bancos"])
    @commands.guild_only()
    async def estabilidade_bancaria(self, ctx):
        dados = self.financeiro.estabilidade_bancaria(ctx.guild.id)
        embed = discord.Embed(title="🏦 Estabilidade Bancária", color=discord.Color.blue())
        embed.add_field(name="Bancos", value=str(dados["bancos"]))
        embed.add_field(name="Status", value=str(dados["status"]).replace("_", " ").title())
        if dados["bancos"]:
            embed.add_field(name="Reservas", value=self.motor.formatar_moeda(dados["reservas_bronze"]))
            embed.add_field(name="Depósitos", value=self.motor.formatar_moeda(dados["depositos_bronze"]))
            embed.add_field(name="Índice de reservas", value=f"{dados['estabilidade'] * 100:.2f}%")
        await ctx.send(embed=embed)

    @commands.command(name="relatorio_monetario", aliases=["banco_central", "politica_monetaria"])
    async def relatorio_monetario(self, ctx):
        estado = self.motor.relatorio_global()
        embed = discord.Embed(title="🏦 Banco Central — Política Monetária", color=discord.Color.blue())
        embed.add_field(name="Taxa de juros", value=f"{float(estado.get('taxa_juros', 0)) * 100:.2f}%")
        embed.add_field(name="Política", value=str(estado.get("politica_monetaria", "estavel")).capitalize())
        embed.add_field(name="Reservas", value=self.motor.formatar_moeda(estado.get("reservas_monetarias_bronze", 0)))
        embed.add_field(name="Crédito", value=self.motor.formatar_moeda(estado.get("credito_disponivel_bronze", 0)))
        embed.add_field(name="Inflação/minuto", value=f"{float(estado.get('inflacao_minuto', 0)) * 100:+.4f}%")
        await ctx.send(embed=embed)

    @commands.command(name="relatorio_divida", aliases=["divida"])
    @commands.guild_only()
    async def relatorio_divida(self, ctx):
        dividas = list(self.dividas.find({"governo_id": str(ctx.guild.id), "status": {"$ne": "quitada"}}))
        principal = sum(float(d.get("principal_bronze", 0)) for d in dividas)
        saldo = sum(float(d.get("saldo_bronze", 0)) for d in dividas)
        await ctx.send(embed=discord.Embed(title="📊 Dívida Pública", description=f"Títulos ativos: **{len(dividas)}**\nPrincipal: **{self.motor.formatar_moeda(principal)}**\nObrigação atual: **{self.motor.formatar_moeda(saldo)}**", color=discord.Color.gold()))


async def setup(bot):
    await bot.add_cog(BancoCentral(bot))
