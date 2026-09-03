import discord
from discord.ext import commands
from database.python.mongodb import db
from .motor import MotorEconomiaGlobal


class BancoCentral(commands.Cog):
    """Política monetária, liquidez, crédito soberano e dívida pública."""

    def __init__(self, bot):
        self.bot = bot
        self.motor = MotorEconomiaGlobal(db)
        self.dividas = db["Economia_Divida_Publica"]
        self.operacoes = db["Economia_Operacoes_Banco_Central"]

    def _registrar_operacao(self, tipo, valor, guild_id=None, detalhes=None):
        self.operacoes.insert_one({
            "tipo": tipo,
            "valor_bronze": float(valor),
            "governo_id": str(guild_id) if guild_id else None,
            "detalhes": detalhes or {},
        })

    @commands.command(name="definir_juros", aliases=["taxa_juros", "juros"])
    @commands.has_permissions(administrator=True)
    async def definir_juros(self, ctx, percentual: float):
        if percentual < 0 or percentual > 100:
            await ctx.send("❌ A taxa deve estar entre 0% e 100%.")
            return
        estado = self.motor.definir_taxa_juros(percentual / 100)
        self._registrar_operacao("alteracao_juros", 0, ctx.guild.id, {"taxa": percentual / 100})
        embed = discord.Embed(title="🏦 Política de Juros Atualizada", color=discord.Color.blue())
        embed.add_field(name="Taxa de juros", value=f"**{float(estado.get('taxa_juros', 0)) * 100:.2f}%**")
        embed.add_field(name="Efeito", value="Juros maiores restringem o crédito; juros menores estimulam consumo e investimento.", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="injetar_liquidez", aliases=["emitir_moeda"])
    @commands.has_permissions(administrator=True)
    async def injetar_liquidez(self, ctx, valor_bronze: float):
        if valor_bronze <= 0:
            await ctx.send("❌ O valor precisa ser positivo.")
            return
        estado = self.motor.ajustar_liquidez(valor_bronze, "injecao")
        self._registrar_operacao("injecao_liquidez", valor_bronze, ctx.guild.id)
        embed = discord.Embed(title="💰 Liquidez Injetada", color=discord.Color.green())
        embed.add_field(name="Valor", value=self.motor.formatar_moeda(valor_bronze))
        embed.add_field(name="Reservas monetárias", value=self.motor.formatar_moeda(estado.get("reservas_monetarias_bronze", 0)))
        embed.add_field(name="Crédito disponível", value=self.motor.formatar_moeda(estado.get("credito_disponivel_bronze", 0)))
        embed.add_field(name="Risco", value="Expansões excessivas podem elevar a inflação.", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="retirar_liquidez", aliases=["contrair_moeda"])
    @commands.has_permissions(administrator=True)
    async def retirar_liquidez(self, ctx, valor_bronze: float):
        if valor_bronze <= 0:
            await ctx.send("❌ O valor precisa ser positivo.")
            return
        estado = self.motor.ajustar_liquidez(valor_bronze, "retirada")
        retirado = min(float(valor_bronze), float(self.motor.relatorio_global().get("reservas_monetarias_bronze", 0)))
        self._registrar_operacao("retirada_liquidez", retirado, ctx.guild.id)
        embed = discord.Embed(title="🏦 Liquidez Retirada", color=discord.Color.orange())
        embed.add_field(name="Operação solicitada", value=self.motor.formatar_moeda(valor_bronze))
        embed.add_field(name="Reservas restantes", value=self.motor.formatar_moeda(estado.get("reservas_monetarias_bronze", 0)))
        await ctx.send(embed=embed)

    @commands.command(name="emitir_divida", aliases=["divida_publica"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def emitir_divida(self, ctx, valor_bronze: float, juros_percentual: float, prazo_ciclos: int = 1440):
        if valor_bronze <= 0 or juros_percentual < 0 or prazo_ciclos <= 0:
            await ctx.send("❌ Valor, juros e prazo precisam ser positivos.")
            return
        doc = {
            "governo_id": str(ctx.guild.id),
            "principal_bronze": float(valor_bronze),
            "saldo_bronze": float(valor_bronze) * (1 + juros_percentual / 100),
            "taxa_juros": juros_percentual / 100,
            "prazo_ciclos": int(prazo_ciclos),
            "ciclos_restantes": int(prazo_ciclos),
            "status": "aberta",
        }
        self.dividas.insert_one(doc)
        self._registrar_operacao("emissao_divida", valor_bronze, ctx.guild.id, {"juros": juros_percentual, "prazo": prazo_ciclos})
        embed = discord.Embed(title="📜 Dívida Pública Emitida", color=discord.Color.gold())
        embed.add_field(name="Principal", value=self.motor.formatar_moeda(valor_bronze))
        embed.add_field(name="Taxa de juros", value=f"{juros_percentual:.2f}%")
        embed.add_field(name="Prazo", value=f"{prazo_ciclos} ciclos")
        embed.add_field(name="Obrigação total", value=self.motor.formatar_moeda(doc["saldo_bronze"]), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="relatorio_monetario", aliases=["banco_central", "politica_monetaria"])
    async def relatorio_monetario(self, ctx):
        estado = self.motor.relatorio_global()
        embed = discord.Embed(title="🏦 Banco Central — Política Monetária", color=discord.Color.blue())
        embed.add_field(name="Taxa de juros", value=f"{float(estado.get('taxa_juros', 0)) * 100:.2f}%")
        embed.add_field(name="Política", value=str(estado.get("politica_monetaria", "estavel")).capitalize())
        embed.add_field(name="Reservas monetárias", value=self.motor.formatar_moeda(estado.get("reservas_monetarias_bronze", 0)))
        embed.add_field(name="Crédito disponível", value=self.motor.formatar_moeda(estado.get("credito_disponivel_bronze", 0)))
        embed.add_field(name="Índice de preços", value=f"{float(estado.get('indice_precos', 100)):.4f}")
        embed.add_field(name="Inflação/minuto", value=f"{float(estado.get('inflacao_minuto', 0)) * 100:+.4f}%")
        await ctx.send(embed=embed)

    @commands.command(name="relatorio_divida", aliases=["divida"])
    @commands.guild_only()
    async def relatorio_divida(self, ctx):
        dividas = list(self.dividas.find({"governo_id": str(ctx.guild.id), "status": {"$ne": "quitada"}}))
        principal = sum(float(d.get("principal_bronze", 0)) for d in dividas)
        saldo = sum(float(d.get("saldo_bronze", 0)) for d in dividas)
        embed = discord.Embed(title="📊 Dívida Pública", color=discord.Color.gold())
        embed.add_field(name="Títulos ativos", value=str(len(dividas)))
        embed.add_field(name="Principal emitido", value=self.motor.formatar_moeda(principal))
        embed.add_field(name="Obrigação total", value=self.motor.formatar_moeda(saldo))
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(BancoCentral(bot))
