import discord
from bson import ObjectId
from discord.ext import commands
from database.python.mongodb import db
from .motor import MotorEconomiaGlobal
from .trabalho import MotorTrabalho


class Trabalho(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.motor = MotorEconomiaGlobal(db)
        self.trabalho = MotorTrabalho(db, self.motor)

    @commands.command(name="criar_emprego")
    @commands.has_permissions(administrator=True)
    async def criar_emprego(self, ctx, empresa_id: str, cargo: str, vagas: int, salario_bronze: float, produtividade: float = 1.0):
        try:
            oid = ObjectId(empresa_id)
        except Exception:
            await ctx.send("❌ ID de empresa inválido.")
            return
        resultado = self.trabalho.criar_emprego(oid, ctx.guild.id, cargo, vagas, salario_bronze, produtividade)
        embed = discord.Embed(title="👷 Emprego criado", color=discord.Color.green())
        embed.add_field(name="Cargo", value=cargo)
        embed.add_field(name="Vagas", value=str(vagas))
        embed.add_field(name="Salário", value=self.motor.formatar_moeda(salario_bronze))
        embed.add_field(name="ID", value=str(resultado["_id"]), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="contratar")
    @commands.has_permissions(administrator=True)
    async def contratar(self, ctx, emprego_id: str, quantidade: int = 1):
        try:
            oid = ObjectId(emprego_id)
        except Exception:
            await ctx.send("❌ ID de emprego inválido.")
            return
        resultado = self.trabalho.contratar(oid, quantidade)
        if "erro" in resultado:
            await ctx.send(f"❌ {resultado['erro']}")
            return
        await ctx.send(embed=discord.Embed(title="🤝 Contratação concluída", description=f"**{resultado['contratados']}** trabalhadores contratados.\nDesempregados restantes: **{resultado['desempregados']}**", color=discord.Color.green()))

    @commands.command(name="folha_pagamento")
    @commands.has_permissions(administrator=True)
    async def folha_pagamento(self, ctx):
        resultado = self.trabalho.folha_pagamento(ctx.guild.id)
        embed = discord.Embed(title="💰 Folha de Pagamento", color=discord.Color.gold())
        embed.add_field(name="Trabalhadores", value=f"{resultado['trabalhadores']:,}")
        embed.add_field(name="Empresas", value=str(resultado["empresas"]))
        embed.add_field(name="Total pago", value=self.motor.formatar_moeda(resultado["folha_total_bronze"]), inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Trabalho(bot))
