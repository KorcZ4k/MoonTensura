import discord
from discord.ext import commands
from database.python.mongodb import db
from comandos.ECONOMIA.GLOBAL.governo import MotorGoverno


class GovernosAdmin(commands.Cog):
    """Comandos administrativos para criação e gestão de governos."""

    def __init__(self, bot):
        self.bot = bot
        self.motor = MotorGoverno(db, None)
        self.governos = db["Economia_Governos"]
        self.tesouros = db["Economia_Tesouros"]
        self.eventos = db["Economia_Eventos"]

    @commands.command(name="criar_governo_admin")
    @commands.has_permissions(administrator=True)
    async def criar_governo(self, ctx, nome: str, tesouro_inicial: float = 0):
        governo = self.motor.criar_governo(
            guild_id=ctx.guild.id,
            nome=nome,
            tesouro_inicial=tesouro_inicial,
            owner_id=ctx.author.id,
        )
        embed = discord.Embed(title="🏛️ Governo criado", color=discord.Color.green())
        embed.add_field(name="Nome", value=governo["nome"])
        embed.add_field(name="ID", value=f"`{governo['governo_id']}`", inline=False)
        embed.add_field(name="Tesouro inicial", value=f"{max(0, tesouro_inicial):,.0f} Hunos")
        embed.add_field(name="Criado por", value=ctx.author.mention)
        embed.set_footer(text="Cada uso deste comando cria um novo governo; nenhum governo existente é substituído.")
        await ctx.send(embed=embed)

    @commands.command(name="editar_governo")
    @commands.has_permissions(administrator=True)
    async def editar_governo(self, ctx, governo_id: str, campo: str, *, valor: str):
        campo = campo.lower()
        permitidos = {"nome", "status", "autonomia", "controlado_por_jogador", "territorio"}
        if campo not in permitidos:
            await ctx.send("❌ Campos: `nome`, `status`, `autonomia`, `controlado_por_jogador`, `territorio`.")
            return
        valor_final = valor.lower() in {"true", "sim", "s", "1", "ativo"} if campo in {"autonomia", "controlado_por_jogador"} else valor
        resultado = self.governos.update_one(
            {"governo_id": str(governo_id), "guild_id": str(ctx.guild.id)},
            {"$set": {campo: valor_final}},
        )
        if not resultado.matched_count:
            await ctx.send("❌ Governo inexistente neste servidor.")
            return
        self.eventos.insert_one({"tipo": "edicao_governo", "governo_id": str(governo_id), "guild_id": str(ctx.guild.id), "campo": campo, "valor": valor_final, "administrador_id": str(ctx.author.id)})
        await ctx.send(f"✅ Governo `{governo_id}` atualizado: **{campo} = {valor_final}**.")

    @commands.command(name="ver_governo")
    async def ver_governo(self, ctx, governo_id: str):
        governo = self.governos.find_one({"governo_id": str(governo_id), "guild_id": str(ctx.guild.id)})
        if not governo:
            await ctx.send("❌ Governo inexistente neste servidor.")
            return
        tesouro = self.tesouros.find_one({"governo_id": str(governo_id)}) or {}
        embed = discord.Embed(title=f"🏛️ {governo.get('nome', 'Governo')}", color=discord.Color.gold())
        embed.add_field(name="ID", value=f"`{governo_id}`", inline=False)
        embed.add_field(name="Tesouro", value=f"{float(tesouro.get('saldo_bronze', 0)):,.0f} Hunos")
        embed.add_field(name="Status", value=str(governo.get('status', 'ativo')))
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(GovernosAdmin(bot))
