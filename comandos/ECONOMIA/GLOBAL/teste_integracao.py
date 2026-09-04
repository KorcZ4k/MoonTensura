import asyncio
import discord
from discord.ext import commands

from database.python.mongodb import db
from comandos.ECONOMIA.GLOBAL.diagnostico import DiagnosticoEconomiaGlobal
from comandos.ECONOMIA.GLOBAL.validacao import ValidadorEconomia
from comandos.ECONOMIA.GLOBAL.motor import MotorEconomiaGlobal


class TesteIntegracaoEconomia(commands.Cog):
    """Testes seguros da cadeia econômica sem criar dinheiro ou alterar saldos."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="testar_economia")
    @commands.has_permissions(administrator=True)
    async def testar_economia(self, ctx):
        await ctx.send("🔍 Iniciando teste de integração da Economia Global...")

        diagnostico = await asyncio.to_thread(DiagnosticoEconomiaGlobal(db).executar)
        motor = MotorEconomiaGlobal(db)
        validacao = await asyncio.to_thread(ValidadorEconomia(db, motor).executar)

        colecoes = {
            "Hunos": db["Hunos"].count_documents({}),
            "Empresas": db["Economia_Empresas"].count_documents({}),
            "Mercados": db["Mercados"].count_documents({}),
            "Governos": db["Economia_Governos"].count_documents({}),
            "Tesouros": db["Economia_Tesouros"].count_documents({}),
            "Populações": db["Economia_Populacao"].count_documents({}),
            "Rotas": db["Economia_Rotas"].count_documents({}),
        }

        estado = motor.relatorio_global()
        erros = diagnostico.get("erros", 0)
        problemas = validacao.get("total_problemas", 0)
        cor = discord.Color.green() if erros == 0 and problemas == 0 else discord.Color.orange()

        embed = discord.Embed(title="🧪 Teste da Economia Global", color=cor)
        embed.add_field(
            name="Módulos",
            value=f"{diagnostico.get('ok', 0)}/{diagnostico.get('total', 0)} válidos\nSaúde: {diagnostico.get('saude_percentual', 0):.2f}%",
            inline=False,
        )
        embed.add_field(
            name="Validação",
            value=f"Problemas encontrados: {problemas}",
            inline=True,
        )
        embed.add_field(
            name="Estado",
            value=f"Índice de preços: {float(estado.get('indice_precos', 0)):.2f}\nConfiança: {float(estado.get('confianca_economica', 0)):.2f}",
            inline=True,
        )
        embed.add_field(
            name="Dados conectados",
            value="\n".join(f"{nome}: **{quantidade:,}**" for nome, quantidade in colecoes.items()),
            inline=False,
        )
        if erros:
            falhas = [f"• {item['nome']}: {item['erro']}" for item in diagnostico.get('itens', []) if item.get('status') == 'erro']
            embed.add_field(name="Falhas", value="\n".join(falhas)[:1024], inline=False)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TesteIntegracaoEconomia(bot))
