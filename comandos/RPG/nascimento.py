import json
import random
from pathlib import Path

import discord
from discord.ext import commands

from database.python.mongodb import db


BASE_DIR = Path(__file__).resolve().parents[2]
ARQUIVO_HABILIDADES = {
    "Comum": BASE_DIR / "database/json/habilidades/habs_comuns.json",
    "Única": BASE_DIR / "database/json/habilidades/habs_unicas.json",
    "Definitiva": BASE_DIR / "database/json/habilidades/habs_definitivas.json",
    "Suprema": BASE_DIR / "database/json/habilidades/habs_supremas.json",
    "Raça": BASE_DIR / "database/json/habilidades/habs_raca.json",
}
ARQUIVO_FORMAS = BASE_DIR / "database/json/magias/formas.json"
ARQUIVO_ELEMENTOS = BASE_DIR / "database/json/magias/elementos.json"


class Nascimento(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _carregar_lista(self, caminho, chave=None):
        try:
            with open(caminho, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
            if isinstance(dados, list):
                return dados
            if isinstance(dados, dict) and chave:
                return dados.get(chave, [])
        except Exception as erro:
            print(f"Erro ao carregar {caminho}: {erro}")
        return []

    def _sortear_repetidamente(self, catalogo, chance_inicial):
        """Cada obtenção reduz pela metade a chance da próxima."""
        if chance_inicial <= 0 or not catalogo:
            return []

        restantes = list(catalogo)
        sorteadas = []
        chance = float(chance_inicial)

        while restantes and random.random() < chance:
            item = random.choice(restantes)
            restantes.remove(item)
            sorteadas.append(item)
            chance /= 2

        return sorteadas

    def _sortear_habilidades(self, raca):
        resultado = []
        chances = {
            "Comum": 1.0,
            "Única": 0.3,
            "Definitiva": 0.001,
            "Suprema": 0.0,
        }

        for raridade, chance in chances.items():
            catalogo = self._carregar_lista(ARQUIVO_HABILIDADES[raridade])
            resultado.extend(self._sortear_repetidamente(catalogo, chance))

        raciais = self._carregar_lista(ARQUIVO_HABILIDADES["Raça"])
        raca_normalizada = str(raca).strip().lower()

        for habilidade in raciais:
            if not isinstance(habilidade, dict):
                continue
            racas = habilidade.get("racas", [])
            if any(str(item).strip().lower() == raca_normalizada for item in racas):
                resultado.append(habilidade)

        ids = []
        vistos = set()
        for habilidade in resultado:
            if not isinstance(habilidade, dict):
                continue
            habilidade_id = str(
                habilidade.get("ID") or habilidade.get("id") or ""
            ).strip()
            if habilidade_id and habilidade_id not in vistos:
                vistos.add(habilidade_id)
                ids.append(habilidade_id)

        return ids

    def _sortear_magias(self):
        formas = self._carregar_lista(ARQUIVO_FORMAS, "formas")
        elementos = self._carregar_lista(ARQUIVO_ELEMENTOS, "elementos")

        forma = random.choice(formas) if formas else None
        elemento = random.choice(elementos) if elementos else None

        def obter_id(item):
            if isinstance(item, dict):
                return str(item.get("id") or item.get("ID") or "").strip() or None
            return str(item).strip() if item else None

        return obter_id(forma), obter_id(elemento)

    async def _aplicar_dadivas(self, ctx):
        if not ctx.guild:
            return

        jogador = db["Jogadores"].find_one({
            "ID": str(ctx.author.id),
            "guild_id": str(ctx.guild.id),
        })

        if not jogador or jogador.get("Situação") != "ativo":
            return

        if jogador.get("nascimento_sorteado"):
            return

        habilidades = self._sortear_habilidades(jogador.get("Raça", ""))
        forma_id, elemento_id = self._sortear_magias()
        filtro = {
            "ID": str(ctx.author.id),
            "guild_id": str(ctx.guild.id),
        }

        db["Habilidades"].update_one(
            filtro,
            {
                "$set": {
                    "Situação": "ativo",
                    "habilidades": habilidades,
                },
                "$setOnInsert": filtro,
            },
            upsert=True,
        )

        magias = [forma_id] if forma_id else []
        tipos = [elemento_id] if elemento_id else []
        db["Magias"].update_one(
            filtro,
            {
                "$set": {
                    "Situação": "ativo",
                    "magias": magias,
                    "tipos": tipos,
                },
                "$setOnInsert": filtro,
            },
            upsert=True,
        )

        db["Jogadores"].update_one(
            {"_id": jogador["_id"]},
            {"$set": {"nascimento_sorteado": True}}
        )

        embed = discord.Embed(
            title="✨ Dádivas do Nascimento",
            description=(
                f"{ctx.author.mention}, suas habilidades e afinidades "
                "iniciais foram sorteadas automaticamente."
            ),
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name=f"🧠 Habilidades ({len(habilidades)})",
            value="\n".join(f"`{item}`" for item in habilidades) or "Nenhuma.",
            inline=False,
        )
        embed.add_field(
            name="🔷 Forma inicial",
            value=f"`{forma_id}`" if forma_id else "Nenhuma.",
            inline=True,
        )
        embed.add_field(
            name="🌈 Elemento inicial",
            value=f"`{elemento_id}`" if elemento_id else "Nenhum.",
            inline=True,
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        if not ctx.guild or ctx.command is None:
            return

        comando = ctx.command.name

        if comando == "registrar":
            await self._aplicar_dadivas(ctx)
            return

        if comando != "desregistrar":
            return

        # O comando de desregistro já confirmou a operação com sucesso.
        membro = ctx.message.mentions[0] if ctx.message.mentions else None
        if membro is None:
            return

        filtro = {
            "ID": str(membro.id),
            "guild_id": str(ctx.guild.id),
        }

        # Remove integralmente os dados ligados ao personagem anterior.
        db["Magias"].delete_one(filtro)
        db["Habilidades"].delete_one(filtro)
        db["Hunos"].delete_one(filtro)

        # Permite que um novo !registrar gere novas habilidades,
        # formas e elementos para a nova ficha.
        db["Jogadores"].update_one(
            filtro,
            {"$set": {"nascimento_sorteado": False}}
        )

        print(
            f"🧹 Dados de nascimento removidos para "
            f"{membro.id} no servidor {ctx.guild.id}."
        )


async def setup(bot):
    await bot.add_cog(Nascimento(bot))
