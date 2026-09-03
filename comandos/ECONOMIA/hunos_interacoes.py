import datetime
import random

import discord
from discord.ext import commands

from database.python.mongodb import db
from database.python.Hunos import (
    adicionar_hunos,
    obter_hunos,
    pagar_hunos,
    depositar_hunos,
    sacar_hunos,
)


COOLDOWNS = {
    "work": 3600,
    "slut": 3600,
    "rob": 3600,
    "beg": 1800,
    "crime": 7200,
    "daily": 86400,
    "monthly": 2592000,
}


class HunosInteracoes(commands.Cog):
    """Comandos econômicos de interação usando exclusivamente Hunos."""

    def __init__(self, bot):
        self.bot = bot
        self.collection = db["Hunos"]

    def _now(self):
        return datetime.datetime.now(datetime.timezone.utc)

    def _cooldown(self, user_id, guild_id, comando):
        documento = self.collection.find_one(
            {"ID": str(user_id), "guild_id": str(guild_id)},
            {"cooldowns": 1}
        ) or {}
        ultimo = (documento.get("cooldowns", {}) or {}).get(comando)
        if not ultimo:
            return 0
        if isinstance(ultimo, str):
            try:
                ultimo = datetime.datetime.fromisoformat(ultimo)
            except ValueError:
                return 0
        if ultimo.tzinfo is None:
            ultimo = ultimo.replace(tzinfo=datetime.timezone.utc)
        restante = COOLDOWNS[comando] - (self._now() - ultimo).total_seconds()
        return max(0, int(restante))

    def _registrar_cooldown(self, user_id, guild_id, comando):
        self.collection.update_one(
            {"ID": str(user_id), "guild_id": str(guild_id)},
            {
                "$set": {f"cooldowns.{comando}": self._now()},
                "$setOnInsert": {
                    "ID": str(user_id),
                    "guild_id": str(guild_id),
                    "carteira": 0,
                    "banco": 0,
                },
            },
            upsert=True,
        )

    def _tempo(self, segundos):
        horas, resto = divmod(segundos, 3600)
        minutos, segundos = divmod(resto, 60)
        partes = []
        if horas:
            partes.append(f"{horas}h")
        if minutos:
            partes.append(f"{minutos}min")
        if segundos and not horas:
            partes.append(f"{segundos}s")
        return " ".join(partes) or "0s"

    async def _ganhar(self, ctx, comando, minimo, maximo, titulo, texto):
        restante = self._cooldown(ctx.author.id, ctx.guild.id, comando)
        if restante > 0:
            await ctx.send(embed=discord.Embed(
                title="⏳ Cooldown",
                description=f"Tente novamente em **{self._tempo(restante)}**.",
                color=discord.Color.orange(),
            ))
            return

        quantidade = random.randint(minimo, maximo)
        try:
            adicionar_hunos(ctx.author.id, ctx.guild.id, quantidade)
        except ValueError:
            self.collection.update_one(
                {"ID": str(ctx.author.id), "guild_id": str(ctx.guild.id)},
                {"$setOnInsert": {"carteira": 0, "banco": 0}},
                upsert=True,
            )
            adicionar_hunos(ctx.author.id, ctx.guild.id, quantidade)

        self._registrar_cooldown(ctx.author.id, ctx.guild.id, comando)
        await ctx.send(embed=discord.Embed(
            title=titulo,
            description=f"{texto}\n\n💰 Você recebeu **{quantidade:,} Hunos**.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        ))

    @commands.command(name="work", aliases=["trabalhar"])
    @commands.guild_only()
    async def work(self, ctx):
        await self._ganhar(ctx, "work", 100, 1000, "💼 Trabalho", "Você trabalhou e recebeu sua remuneração.")

    @commands.command(name="slut")
    @commands.guild_only()
    async def slut(self, ctx):
        await self._ganhar(ctx, "slut", 50, 800, "💋 Interação", "Sua interação foi recompensada.")

    @commands.command(name="beg", aliases=["mendigar"])
    @commands.guild_only()
    async def beg(self, ctx):
        await self._ganhar(ctx, "beg", 25, 300, "🪙 Ajuda", "Alguém decidiu ajudar você.")

    @commands.command(name="crime", aliases=["crime"])
    @commands.guild_only()
    async def crime(self, ctx):
        restante = self._cooldown(ctx.author.id, ctx.guild.id, "crime")
        if restante > 0:
            await ctx.send(embed=discord.Embed(title="⏳ Cooldown", description=f"Tente novamente em **{self._tempo(restante)}**.", color=discord.Color.orange()))
            return
        self._registrar_cooldown(ctx.author.id, ctx.guild.id, "crime")
        if random.random() < 0.55:
            quantidade = random.randint(250, 2500)
            try:
                adicionar_hunos(ctx.author.id, ctx.guild.id, quantidade)
            except ValueError:
                self.collection.update_one({"ID": str(ctx.author.id), "guild_id": str(ctx.guild.id)}, {"$setOnInsert": {"carteira": 0, "banco": 0}}, upsert=True)
                adicionar_hunos(ctx.author.id, ctx.guild.id, quantidade)
            descricao = f"O crime deu certo. Você obteve **{quantidade:,} Hunos**."
            cor = discord.Color.green()
        else:
            saldo = obter_hunos(ctx.author.id, ctx.guild.id)["carteira"]
            perda = min(saldo, random.randint(100, 1000))
            if perda:
                self.collection.update_one({"ID": str(ctx.author.id), "guild_id": str(ctx.guild.id)}, {"$inc": {"carteira": -perda}})
            descricao = f"O crime falhou. Você perdeu **{perda:,} Hunos**."
            cor = discord.Color.red()
        await ctx.send(embed=discord.Embed(title="🕵️ Crime", description=descricao, color=cor))

    @commands.command(name="rob", aliases=["roubar"])
    @commands.guild_only()
    async def rob(self, ctx, alvo: discord.Member):
        if alvo.bot or alvo.id == ctx.author.id:
            await ctx.send("❌ Escolha outro jogador.")
            return
        restante = self._cooldown(ctx.author.id, ctx.guild.id, "rob")
        if restante > 0:
            await ctx.send(embed=discord.Embed(title="⏳ Cooldown", description=f"Tente novamente em **{self._tempo(restante)}**.", color=discord.Color.orange()))
            return
        self._registrar_cooldown(ctx.author.id, ctx.guild.id, "rob")
        saldo_alvo = obter_hunos(alvo.id, ctx.guild.id)["carteira"]
        if saldo_alvo <= 0:
            await ctx.send(embed=discord.Embed(title="🦹 Roubo", description="O alvo não possui Hunos na carteira.", color=discord.Color.red()))
            return
        if random.random() < 0.45:
            quantidade = min(saldo_alvo, random.randint(1, max(1, int(saldo_alvo * 0.25))))
            self.collection.update_one({"ID": str(alvo.id), "guild_id": str(ctx.guild.id), "carteira": {"$gte": quantidade}}, {"$inc": {"carteira": -quantidade}})
            try:
                adicionar_hunos(ctx.author.id, ctx.guild.id, quantidade)
            except ValueError:
                self.collection.update_one({"ID": str(ctx.author.id), "guild_id": str(ctx.guild.id)}, {"$setOnInsert": {"carteira": quantidade, "banco": 0}}, upsert=True)
            texto = f"Você roubou **{quantidade:,} Hunos** de {alvo.mention}."
            cor = discord.Color.green()
        else:
            multa = min(obter_hunos(ctx.author.id, ctx.guild.id)["carteira"], random.randint(50, 500))
            if multa:
                self.collection.update_one({"ID": str(ctx.author.id), "guild_id": str(ctx.guild.id)}, {"$inc": {"carteira": -multa}})
            texto = f"Você falhou no roubo e perdeu **{multa:,} Hunos**."
            cor = discord.Color.red()
        await ctx.send(embed=discord.Embed(title="🦹 Roubo", description=texto, color=cor))

    @commands.command(name="pay")
    @commands.guild_only()
    async def pay(self, ctx, alvo: discord.Member, quantidade: int):
        if alvo.bot or alvo.id == ctx.author.id or quantidade <= 0:
            await ctx.send("❌ Informe um jogador válido e uma quantidade maior que zero.")
            return
        try:
            pagar_hunos(ctx.author.id, alvo.id, ctx.guild.id, quantidade)
        except ValueError as erro:
            await ctx.send(f"❌ {erro}")
            return
        await ctx.send(embed=discord.Embed(title="💸 Pagamento", description=f"{ctx.author.mention} pagou **{quantidade:,} Hunos** para {alvo.mention}.", color=discord.Color.green()))

    @commands.command(name="dep")
    @commands.guild_only()
    async def dep(self, ctx, quantidade: int):
        try:
            saldo = depositar_hunos(ctx.author.id, ctx.guild.id, quantidade)
        except ValueError as erro:
            await ctx.send(f"❌ {erro}")
            return
        await ctx.send(embed=discord.Embed(title="🏦 Depósito", description=f"💰 Carteira: **{saldo['carteira']:,}**\n🏦 Banco: **{saldo['banco']:,}**", color=discord.Color.green()))

    @commands.command(name="with", aliases=["withdraw"])
    @commands.guild_only()
    async def with_cmd(self, ctx, quantidade: int):
        try:
            saldo = sacar_hunos(ctx.author.id, ctx.guild.id, quantidade)
        except ValueError as erro:
            await ctx.send(f"❌ {erro}")
            return
        await ctx.send(embed=discord.Embed(title="🏦 Saque", description=f"💰 Carteira: **{saldo['carteira']:,}**\n🏦 Banco: **{saldo['banco']:,}**", color=discord.Color.green()))

    @commands.command(name="bal", aliases=["balance"])
    @commands.guild_only()
    async def bal(self, ctx, membro: discord.Member = None):
        membro = membro or ctx.author
        saldo = obter_hunos(membro.id, ctx.guild.id)
        await ctx.send(embed=discord.Embed(title=f"💰 Hunos de {membro.display_name}", description=f"Carteira: **{saldo['carteira']:,}**\nBanco: **{saldo['banco']:,}**\nTotal: **{saldo['carteira'] + saldo['banco']:,}**", color=discord.Color.gold()))


async def setup(bot):
    await bot.add_cog(HunosInteracoes(bot))
