import discord
from discord.ext import commands
from database.python.mongodb import db
from database.python.Hunos import get_hunos, remover_hunos, adicionar_hunos
from datetime import datetime, timezone


class EmpresasMembros(commands.Cog):
    """Empresas controladas por jogadores."""

    def __init__(self, bot):
        self.bot = bot
        self.empresas = db["Economia_Empresas"]
        self.eventos = db["Economia_Eventos"]

    @commands.command(name="criar_minha_empresa")
    async def criar_minha_empresa(self, ctx, nome: str, tipo: str, capital_inicial: int):
        capital_inicial = int(capital_inicial)
        if capital_inicial <= 0:
            await ctx.send("❌ O capital inicial deve ser maior que zero.")
            return
        saldo = get_hunos(str(ctx.author.id), str(ctx.guild.id))
        if saldo < capital_inicial:
            await ctx.send(f"❌ Você não possui Hunos suficientes. Disponível: **{saldo:,.0f} Hunos**.")
            return
        if self.empresas.find_one({"guild_id": str(ctx.guild.id), "nome": nome}):
            await ctx.send("❌ Já existe uma empresa com esse nome neste servidor.")
            return
        try:
            remover_hunos(ctx.author.id, ctx.guild.id, capital_inicial)
        except Exception as erro:
            await ctx.send(f"❌ Não foi possível transferir os Hunos: {erro}")
            return
        documento = {
            "guild_id": str(ctx.guild.id), "nome": nome, "tipo": tipo,
            "dono_id": str(ctx.author.id), "controlado_por_jogador": True,
            "autonomia": False, "status": "ativa",
            "caixa_bronze": float(capital_inicial), "capital_bronze": float(capital_inicial),
            "receita_bronze": 0.0, "custos_bronze": 0.0,
            "lucro_liquido_bronze": 0.0, "criado_em": datetime.now(timezone.utc),
        }
        self.empresas.insert_one(documento)
        self.eventos.insert_one({"tipo": "empresa_criada_jogador", "empresa": nome, "dono_id": str(ctx.author.id), "guild_id": str(ctx.guild.id)})
        await ctx.send(f"🏢 Empresa **{nome}** criada com **{capital_inicial:,.0f} Hunos** de capital.")

    @commands.command(name="minhas_empresas")
    async def minhas_empresas(self, ctx):
        empresas = list(self.empresas.find({"guild_id": str(ctx.guild.id), "dono_id": str(ctx.author.id)}))
        if not empresas:
            await ctx.send("📭 Você ainda não possui empresas.")
            return
        linhas = []
        for empresa in empresas[:20]:
            linhas.append(f"**{empresa.get('nome')}** — {empresa.get('tipo', 'geral')} | Caixa: {float(empresa.get('caixa_bronze', 0)):,.0f} Hunos")
        await ctx.send("🏢 **Suas empresas:**\n" + "\n".join(linhas))

    @commands.command(name="minha_empresa")
    async def minha_empresa(self, ctx, *, nome: str):
        empresa = self.empresas.find_one({"guild_id": str(ctx.guild.id), "nome": nome, "dono_id": str(ctx.author.id)})
        if not empresa:
            await ctx.send("❌ Empresa não encontrada ou você não é o proprietário.")
            return
        embed = discord.Embed(title=f"🏢 {empresa['nome']}", color=discord.Color.blue())
        embed.add_field(name="Tipo", value=empresa.get("tipo", "geral"))
        embed.add_field(name="Status", value=empresa.get("status", "ativa"))
        embed.add_field(name="Caixa", value=f"{float(empresa.get('caixa_bronze', 0)):,.0f} Hunos")
        embed.add_field(name="Receita", value=f"{float(empresa.get('receita_bronze', 0)):,.0f} Hunos")
        embed.add_field(name="Custos", value=f"{float(empresa.get('custos_bronze', 0)):,.0f} Hunos")
        embed.add_field(name="Lucro", value=f"{float(empresa.get('lucro_liquido_bronze', 0)):,.0f} Hunos")
        await ctx.send(embed=embed)

    @commands.command(name="investir_empresa")
    async def investir_empresa(self, ctx, quantidade: int, *, nome: str):
        quantidade = int(quantidade)
        if quantidade <= 0:
            await ctx.send("❌ A quantidade deve ser maior que zero.")
            return
        empresa = self.empresas.find_one({"guild_id": str(ctx.guild.id), "nome": nome, "dono_id": str(ctx.author.id)})
        if not empresa:
            await ctx.send("❌ Empresa não encontrada.")
            return
        if get_hunos(str(ctx.author.id), str(ctx.guild.id)) < quantidade:
            await ctx.send("❌ Você não possui Hunos suficientes.")
            return
        try:
            remover_hunos(ctx.author.id, ctx.guild.id, quantidade)
        except Exception as erro:
            await ctx.send(f"❌ Erro ao movimentar os Hunos: {erro}")
            return
        self.empresas.update_one({"_id": empresa["_id"]}, {"$inc": {"caixa_bronze": quantidade, "capital_bronze": quantidade}})
        await ctx.send(f"📈 **{quantidade:,.0f} Hunos** investidos em **{nome}**.")

    @commands.command(name="retirar_lucro")
    async def retirar_lucro(self, ctx, quantidade: int, *, nome: str):
        quantidade = int(quantidade)
        if quantidade <= 0:
            await ctx.send("❌ A quantidade deve ser maior que zero.")
            return
        empresa = self.empresas.find_one({"guild_id": str(ctx.guild.id), "nome": nome, "dono_id": str(ctx.author.id)})
        if not empresa:
            await ctx.send("❌ Empresa não encontrada.")
            return
        lucro = max(0.0, float(empresa.get("lucro_liquido_bronze", 0)))
        caixa = max(0.0, float(empresa.get("caixa_bronze", 0)))
        disponivel = min(lucro, caixa)
        if quantidade > disponivel:
            await ctx.send(f"❌ Disponível para retirada: **{disponivel:,.0f} Hunos**.")
            return
        self.empresas.update_one({"_id": empresa["_id"]}, {"$inc": {"caixa_bronze": -quantidade, "lucro_liquido_bronze": -quantidade}})
        adicionar_hunos(ctx.author.id, ctx.guild.id, quantidade)
        await ctx.send(f"💰 Você retirou **{quantidade:,.0f} Hunos** de **{nome}**.")


async def setup(bot):
    await bot.add_cog(EmpresasMembros(bot))
