import json
import os
import random
import asyncio
import discord
from discord.ext import commands


ARQUIVO_DANOS = "database/json/habilidades/danos.json"


class UsarHabilidade(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.danos = self._carregar_danos()

    def _carregar_danos(self):
        try:
            with open(ARQUIVO_DANOS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Erro ao carregar danos.json: {e}")
            return {"padrao": {}, "habilidades": {}}

    def _normalizar(self, texto):
        return str(texto or "").strip().casefold()

    def _buscar_habilidade_por_nome(self, nome):
        cog = self.bot.get_cog("Habilidades")
        if not cog:
            return None
        procurado = self._normalizar(nome)
        for habilidade in cog.cache_habilidades.values():
            if self._normalizar(habilidade.get("nome")) == procurado:
                return habilidade
        return None

    def _jogador_possui(self, user_id, guild_id, habilidade_id):
        from database.python.mongodb import db
        if db is None:
            return False
        doc = db["Habilidades"].find_one({
            "ID": str(user_id),
            "guild_id": str(guild_id)
        })
        if not doc:
            return False
        habilidades = doc.get("habilidades", [])
        if isinstance(habilidades, str):
            habilidades = [x.strip().strip("\"'") for x in habilidades.replace("[", "").replace("]", "").split(",")]
        for item in habilidades:
            if isinstance(item, dict):
                item = item.get("id") or item.get("ID")
            if str(item).strip() == str(habilidade_id):
                return True
        return False

    @commands.command(name="usarhab")
    async def usarhab(self, ctx, *, nome: str = None):
        if not nome:
            await ctx.send("❌ Use: `!usarhab <nome da habilidade>`")
            return

        habilidade = self._buscar_habilidade_por_nome(nome)
        if not habilidade:
            await ctx.send(f"❌ Não encontrei nenhuma habilidade chamada **{nome}**.")
            return

        if self._normalizar(habilidade.get("ativa")) not in ("sim", "true", "ativa", "yes", "1"):
            await ctx.send(f"❌ **{habilidade['nome']}** é uma habilidade passiva e não pode ser usada diretamente em combate.")
            return

        if not self._jogador_possui(ctx.author.id, ctx.guild.id, habilidade["id"]):
            await ctx.send("❌ Você não possui essa habilidade.")
            return

        luta = self.bot.get_cog("Luta")
        if not luta:
            await ctx.send("❌ Sistema de luta não está carregado.")
            return

        combate = luta.combates.get(ctx.channel.id)
        if not combate or not combate.get("ativo"):
            await ctx.send("❌ `!usarhab` só pode ser usado durante uma batalha.")
            return

        if combate.get("fase") != "ataque":
            await ctx.send("❌ O ataque anterior ainda precisa ser defendido.")
            return

        atacante = luta._obter_atacante(combate)
        defensor = luta._obter_defensor(combate)

        if atacante.get("tipo") != "jogador" or atacante.get("id") != str(ctx.author.id):
            await ctx.send(f"❌ Não é sua vez. Agora é a vez de **{atacante.get('nome', 'outro participante')}**.")
            return

        configuracao = dict(self.danos.get("padrao", {}))
        configuracao.update(self.danos.get("habilidades", {}).get(str(habilidade["id"]), {}))

        mana = float(atacante.get("mana", 0) or 0)
        gasto = float(configuracao.get("gasto_mana", 0) or 0)
        if mana < gasto:
            await ctx.send(f"❌ Mana insuficiente. Necessário: **{gasto:g}** | Atual: **{mana:g}**")
            return

        atacante["mana"] = mana - gasto
        combate["ataque_pendente"] = {
            "atacante_id": atacante["id"],
            "defensor_id": defensor["id"],
            "tipo": "habilidade",
            "nome": f"✨ {habilidade['nome']}",
            "habilidade": habilidade,
            "config": configuracao
        }
        combate["fase"] = "defesa"

        embed = discord.Embed(
            title=f"✨ Turno {combate['numero_turno']} — Habilidade",
            description=(
                f"**{atacante['nome']}** usou **{habilidade['nome']}** contra **{defensor['nome']}**!\n"
                f"💙 Mana gasta: **{gasto:g}**\n\n"
                f"🛡️ **{defensor['nome']}** deve usar `!defesa` ou `!esquiva`."
            ),
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

        if defensor.get("tipo") == "monstro":
            await asyncio.sleep(1)
            await luta._defesa_monstro(ctx)


async def setup(bot):
    await bot.add_cog(UsarHabilidade(bot))
