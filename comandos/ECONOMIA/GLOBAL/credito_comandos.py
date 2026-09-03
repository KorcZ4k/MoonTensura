import discord
from discord.ext import commands
from database.python.mongodb import db
from .motor import MotorEconomiaGlobal
from .credito import MotorCredito


class Credito(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.motor = MotorEconomiaGlobal(db)
        self.credito = MotorCredito(db, self.motor)

    @commands.command(name="credito", aliases=["score_credito"])
    async def score_credito(self, ctx):
        perfil = self.credito._perfil(ctx.author.id)
        embed = discord.Embed(title="💳 Perfil de Crédito", color=discord.Color.blue())
        embed.add_field(name="Score", value=f"{perfil['score']:.0f}/1000")
        embed.add_field(name="Dívida", value=self.motor.formatar_moeda(perfil['divida']))
        embed.add_field(name="Inadimplências", value=str(perfil['atrasados']))
        await ctx.send(embed=embed)

    @commands.command(name="emprestimo", aliases=["solicitar_emprestimo"])
    async def emprestimo(self, ctx, banco: str, valor: float, parcelas: int = 10, garantia: float = 0):
        resultado = self.credito.solicitar(ctx.author.id, banco, valor, parcelas, garantia)
        if "erro" in resultado:
            msg = "Crédito negado devido ao risco." if resultado["erro"] == "credito_negado" else "Banco não encontrado ou valor inválido."
            await ctx.send(embed=discord.Embed(title="❌ Empréstimo", description=msg, color=discord.Color.red())); return
        e = resultado["emprestimo"]
        embed = discord.Embed(title="💰 Empréstimo Aprovado", color=discord.Color.green())
        embed.add_field(name="Principal", value=self.motor.formatar_moeda(e["principal_bronze"]))
        embed.add_field(name="Juros", value=f"{e['taxa_juros'] * 100:.2f}%")
        embed.add_field(name="Parcelas", value=f"{e['parcelas_total']} × {self.motor.formatar_moeda(e['valor_parcela_bronze'])}")
        embed.add_field(name="ID", value=str(e.get("_id", "gerado")), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="pagar_emprestimo", aliases=["pagar_parcela"])
    async def pagar_emprestimo(self, ctx, emprestimo_id: str):
        resultado = self.credito.pagar_parcela(ctx.author.id, emprestimo_id)
        if "erro" in resultado:
            await ctx.send(embed=discord.Embed(title="❌ Pagamento", description=f"Não foi possível pagar: **{resultado['erro']}**", color=discord.Color.red())); return
        await ctx.send(embed=discord.Embed(title="✅ Parcela Paga", description=f"Pago: **{self.motor.formatar_moeda(resultado['pago'])}**\nSaldo restante: **{self.motor.formatar_moeda(resultado['saldo'])}**", color=discord.Color.green()))


async def setup(bot):
    await bot.add_cog(Credito(bot))
