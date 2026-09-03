import random
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from database.python.mongodb import db


FUSO_BRASIL = timezone(timedelta(hours=-3))
COOLDOWN_DAILY = timedelta(hours=24)
COOLDOWN_MONTHLY = timedelta(days=30)


class Recompensas(commands.Cog):
    """Recompensas periódicas da economia de Mora."""

    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = db["EconomiaCooldowns"]
        self.mora = db["Mora"]

    @staticmethod
    def _agora():
        return datetime.now(FUSO_BRASIL)

    @staticmethod
    def _formatar_tempo(delta):
        segundos = max(0, int(delta.total_seconds()))
        dias, segundos = divmod(segundos, 86400)
        horas, segundos = divmod(segundos, 3600)
        minutos, _ = divmod(segundos, 60)

        partes = []

        if dias:
            partes.append(f"{dias}d")
        if horas:
            partes.append(f"{horas}h")
        if minutos or not partes:
            partes.append(f"{minutos}min")

        return " ".join(partes)

    async def _resgatar(
        self,
        ctx,
        tipo,
        minimo,
        maximo,
        cooldown
    ):
        agora = self._agora()
        chave = {
            "ID": str(ctx.author.id),
            "guild_id": str(ctx.guild.id),
            "tipo": tipo
        }

        registro = self.cooldowns.find_one(chave)

        if registro:
            ultimo_resgate = registro.get("ultimo_resgate")

            if ultimo_resgate:
                if ultimo_resgate.tzinfo is None:
                    ultimo_resgate = ultimo_resgate.replace(
                        tzinfo=FUSO_BRASIL
                    )

                proximo_resgate = ultimo_resgate + cooldown

                if agora < proximo_resgate:
                    restante = proximo_resgate - agora

                    embed = discord.Embed(
                        title="⏳ | Recompensa indisponível",
                        description=(
                            f"{ctx.author.mention}, você já resgatou "
                            f"sua recompensa **{tipo}**.\n\n"
                            f"Tente novamente em **{self._formatar_tempo(restante)}**."
                        ),
                        color=discord.Color.orange(),
                        timestamp=agora
                    )
                    embed.set_footer(
                        text="Tensura Moon - Korczak Technologies!"
                    )
                    await ctx.send(embed=embed)
                    return

        quantidade = random.randint(minimo, maximo)

        self.mora.update_one(
            {
                "ID": str(ctx.author.id),
                "guild_id": str(ctx.guild.id)
            },
            {
                "$inc": {
                    "carteira": quantidade
                },
                "$setOnInsert": {
                    "banco": 0
                }
            },
            upsert=True
        )

        self.cooldowns.update_one(
            chave,
            {
                "$set": {
                    "ultimo_resgate": agora
                }
            },
            upsert=True
        )

        nome = "Recompensa diária" if tipo == "daily" else "Recompensa mensal"

        embed = discord.Embed(
            title=f"🎁 | {nome}",
            description=(
                f"{ctx.author.mention}, você recebeu "
                f"**{quantidade:,} Mora**!"
            ),
            color=discord.Color.green(),
            timestamp=agora
        )

        embed.add_field(
            name="💰 Recompensa",
            value=f"**{quantidade:,} Mora**",
            inline=False
        )

        embed.set_footer(
            text="Tensura Moon - Korczak Technologies!"
        )

        await ctx.send(embed=embed)

    @commands.command(name="daily")
    async def daily(self, ctx):
        """Recebe entre 100 e 1000 Mora a cada 24 horas."""
        await self._resgatar(
            ctx,
            "daily",
            100,
            1000,
            COOLDOWN_DAILY
        )

    @commands.command(name="monthly")
    async def monthly(self, ctx):
        """Recebe entre 1000 e 10000 Mora a cada 30 dias."""
        await self._resgatar(
            ctx,
            "monthly",
            1000,
            10000,
            COOLDOWN_MONTHLY
        )


async def setup(bot):
    await bot.add_cog(Recompensas(bot))
