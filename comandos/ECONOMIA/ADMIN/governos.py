import discord
from discord.ext import commands
from database.python.mongodb import db
from comandos.ECONOMIA.GLOBAL.governo import MotorGoverno


class GovernosAdmin(commands.Cog):
    """Comandos administrativos para governos e tesouros públicos."""

    def __init__(self, bot):
        self.bot = bot
        self.motor = MotorGoverno(db, None)
        self.governos = db["Economia_Governos"]
        self.tesouros = db["Economia_Tesouros"]
        self.eventos = db["Economia_Eventos"]

    @commands.command(name="criar_governo_admin")
    @commands.has_permissions(administrator=True)
    async def criar_governo(self, ctx, nome: str, tesouro_inicial: float = 0):
        governo = self.motor.criar_governo(ctx.guild.id, nome, tesouro_inicial)
        await ctx.send(f"🏛️ Governo **{governo['nome']}** criado. Tesouro inicial: **{max(0, tesouro_inicial):,.0f} Hunos**.")

    @commands.command(name="editar_governo")
    @commands.has_permissions(administrator=True)
    async def editar_governo(self, ctx, campo: str, *, valor: str):
        campo = campo.lower()
        permitidos = {"nome", "status", "autonomia", "controlado_por_jogador", "territorio"}
        if campo not in permitidos:
            await ctx.send("❌ Campos: `nome`, `status`, `autonomia`, `controlado_por_jogador`, `territorio`.")
            return
        valor_final = valor.lower() in {"true", "sim", "s", "1", "ativo"} if campo in {"autonomia", "controlado_por_jogador"} else valor
        resultado = self.governos.update_one({"governo_id": str(ctx.guild.id)}, {"$set": {campo: valor_final}})
        if not resultado.matched_count:
            await ctx.send("❌ Governo inexistente. Use `!criar_governo` primeiro.")
            return
        self.eventos.insert_one({"tipo": "edicao_governo", "governo_id": str(ctx.guild.id), "campo": campo, "valor": valor_final, "administrador_id": str(ctx.author.id)})
        await ctx.send(f"✅ Governo atualizado: **{campo} = {valor_final}**.")

    @commands.command(name="definir_imposto_admin")
    @commands.has_permissions(administrator=True)
    async def definir_imposto(self, ctx, tipo: str, percentual: float):
        resultado = self.motor.definir_imposto(ctx.guild.id, tipo, percentual / 100)
        if "erro" in resultado:
            await ctx.send("❌ Tipo inválido ou governo inexistente.")
            return
        await ctx.send(f"📊 Imposto de **{tipo}** definido para **{resultado['aliquota'] * 100:.2f}%**.")

    @commands.command(name="definir_tarifa_admin")
    @commands.has_permissions(administrator=True)
    async def definir_tarifa(self, ctx, tipo: str, percentual: float):
        resultado = self.motor.definir_tarifa(ctx.guild.id, tipo, percentual / 100)
        if "erro" in resultado:
            await ctx.send("❌ Tipo inválido ou governo inexistente.")
            return
        await ctx.send(f"🚢 Tarifa de **{tipo}** definida para **{resultado['aliquota'] * 100:.2f}%**.")

    @commands.command(name="injetar_liquidez_governo")
    @commands.has_permissions(administrator=True)
    async def injetar_liquidez(self, ctx, quantidade: float, *, motivo: str = "Intervenção administrativa"):
        quantidade = float(quantidade)
        if quantidade <= 0:
            await ctx.send("❌ A quantidade deve ser maior que zero.")
            return
        tesouro = self.tesouros.find_one({"governo_id": str(ctx.guild.id)})
        if not tesouro:
            await ctx.send("❌ Governo ou tesouro inexistente.")
            return
        self.tesouros.update_one({"_id": tesouro["_id"]}, {"$inc": {"saldo_bronze": quantidade, "liquidez_injetada_bronze": quantidade}})
        self.eventos.insert_one({"tipo": "injecao_liquidez_governo", "governo_id": str(ctx.guild.id), "quantidade_hunos": quantidade, "motivo": motivo, "administrador_id": str(ctx.author.id)})
        await ctx.send(f"💉 **{quantidade:,.0f} Hunos** foram injetados no tesouro.\nMotivo: {motivo}")

    @commands.command(name="ver_governo")
    async def ver_governo(self, ctx):
        dados = self.motor.relatorio(ctx.guild.id)
        if "erro" in dados:
            await ctx.send("❌ Não existe um governo configurado para este servidor.")
            return
        governo = dados["governo"]
        tesouro = dados.get("tesouro", {})
        embed = discord.Embed(title=f"🏛️ {governo.get('nome', 'Governo')}", color=discord.Color.gold())
        embed.add_field(name="Tesouro", value=f"{float(tesouro.get('saldo_bronze', 0)):,.0f} Hunos")
        embed.add_field(name="Status", value=str(governo.get('status', 'ativo')))
        embed.add_field(name="Autonomia", value="Ativa" if governo.get('autonomia', True) else "Desativada")
        taxas = governo.get("taxas", {})
        if taxas:
            texto = "\n".join(f"{k}: {float(v) * 100:.2f}%" for k, v in taxas.items())
            embed.add_field(name="Impostos", value=texto[:1024], inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(GovernosAdmin(bot))
