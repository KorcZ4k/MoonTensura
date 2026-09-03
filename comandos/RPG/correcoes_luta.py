import asyncio
import types

import discord
from discord.ext import commands


class CorrecoesLuta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._aplicar_correcoes()

    def _aplicar_correcoes(self):
        luta = self.bot.get_cog("Luta")
        if luta is None:
            print("⚠️ Luta não carregada; correção de magia defensiva não aplicada.")
            return

        if getattr(luta, "_magia_defensiva_corrigida", False):
            return

        original_usar_magia = luta.usar_magia_no_combate
        original_resolver = luta._resolver_ataque

        async def usar_magia_corrigida(cog, ctx, dados_magia):
            tipos = [str(tipo).strip().lower() for tipo in dados_magia.get("tipos", [])]
            defesa_base = float(dados_magia.get("defesa_base", 0) or 0)

            efeito = dados_magia.get("efeito", {})
            nome_efeito = ""
            if isinstance(efeito, dict):
                nome_efeito = str(efeito.get("nome", "")).strip().lower()

            defensiva = (
                "defesa" in tipos
                or "protecao" in tipos
                or "proteção" in tipos
                or defesa_base > 0
                or nome_efeito in {"barreira", "escudo", "proteção", "protecao"}
            )

            if not defensiva:
                return await original_usar_magia(ctx, dados_magia)

            combate = cog._obter_combate(ctx.channel.id)
            if not combate or not combate.get("ativo"):
                return False

            if combate.get("aguardando_finalizacao") or combate.get("fase") != "ataque":
                await ctx.send("❌ Essa magia não pode ser usada agora.")
                return True

            usuario = cog._obter_atacante(combate)
            if usuario.get("tipo") != "jogador" or usuario.get("id") != str(ctx.author.id):
                await ctx.send("❌ Não é sua vez de agir.")
                return True

            mana_base = int(dados_magia.get("mana_base", 0) or 0)
            mana_atual = int(usuario.get("mana", 0) or 0)
            if mana_atual < mana_base:
                await ctx.send(f"❌ Mana insuficiente. Necessário: {mana_base}.")
                return True

            usuario["mana"] = mana_atual - mana_base
            bonus = int(defesa_base or (efeito.get("valor", 0) if isinstance(efeito, dict) else 0) or 0)
            bonus = max(0, bonus)

            usuario["defesa"] = float(usuario.get("defesa", 0) or 0) + bonus
            usuario["defesa_bonus_magica"] = bonus
            usuario["defesa_ativa"] = True
            usuario["esquiva_ativa"] = False

            nome = dados_magia.get("nome", "Magia Defensiva")
            embed = discord.Embed(
                title="🛡️ Magia Defensiva",
                description=(
                    f"✨ **{usuario['nome']}** utilizou **{nome}** para se proteger.\n"
                    f"🛡️ Defesa adicional: **{bonus}**\n"
                    f"💙 Mana gasta: **{mana_base}**"
                ),
                color=discord.Color.blue(),
            )
            await ctx.send(embed=embed)
            await asyncio.sleep(0.5)
            await cog._proximo_turno(ctx)
            return True

        async def resolver_corrigido(cog, ctx):
            combate = cog._obter_combate(ctx.channel.id)
            defensor = cog._obter_defensor(combate) if combate else None
            bonus = 0
            if defensor:
                bonus = float(defensor.get("defesa_bonus_magica", 0) or 0)

            resultado = await original_resolver(ctx)

            if defensor and bonus:
                defensor["defesa"] = max(
                    0,
                    float(defensor.get("defesa", 0) or 0) - bonus
                )
                defensor.pop("defesa_bonus_magica", None)

            return resultado

        luta.usar_magia_no_combate = types.MethodType(usar_magia_corrigida, luta)
        luta._resolver_ataque = types.MethodType(resolver_corrigido, luta)
        luta._magia_defensiva_corrigida = True
        print("✅ Magias defensivas corrigidas no sistema de luta.")


async def setup(bot):
    await bot.add_cog(CorrecoesLuta(bot))
