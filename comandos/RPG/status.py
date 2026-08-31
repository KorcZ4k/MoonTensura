"""
Sistema de RPG - Status dos Personagens
Módulo que gerencia status, registro e desregistro de personagens.
"""

import datetime
import json
import random
from pathlib import Path

import discord
from discord.ext import commands

from comandos.RPG.barra_status import barra_mana, barra_vida
from database.python.mongodb import db
from database.python.status import obter_status

# ==========================================
# CONFIGURAÇÃO
# ==========================================

fuso = datetime.timezone(datetime.timedelta(hours=-3))
horario = datetime.datetime.now(fuso)

jogadores = db["Jogadores"]

BASE_DIR = Path(__file__).resolve().parents[2]
RACAS_FILE = BASE_DIR / "database" / "json" / "racas.json"


# ==========================================
# FUNÇÕES UTILITÁRIAS
# ==========================================

def carregar_racas():
    """Carrega as raças do arquivo JSON."""
    with open(RACAS_FILE, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    return dados["racas"]


def sortear_raca():
    """Sorteia uma raça aleatória baseado nas chances."""
    racas = carregar_racas()
    nomes = [raca["nome"] for raca in racas]
    pesos = [raca["chance"] for raca in racas]
    return random.choices(nomes, weights=pesos, k=1)[0]


def obter_dados_raca(nome_raca):
    """Obtém os dados de uma raça específica."""
    racas = carregar_racas()
    for raca in racas:
        if raca["nome"] == nome_raca:
            return raca
    return None


def sortear_atributo():
    """Sorteia um atributo baseado em faixas de força."""
    faixa = random.choice([
        "crianca",
        "muito_fraco",
        "fraco",
        "normal",
        "forte"
    ])

    faixa_valores = {
        "crianca": (0, 50),
        "muito_fraco": (50, 80),
        "fraco": (80, 90),
        "normal": (90, 110),
        "forte": (110, 130)
    }

    min_val, max_val = faixa_valores.get(faixa, (90, 110))
    return random.randint(min_val, max_val)


def aplicar_bonus(valor, bonus):
    """Aplica bônus racial ao atributo."""
    return int(valor * (1 + bonus))


# ==========================================
# COG STATUS
# ==========================================

class Status(commands.Cog):
    """Cog para gerenciar status de personagens do RPG."""

    def __init__(self, bot):
        self.bot = bot

    # ==========================================
    # COMANDO STATUS
    # ==========================================

    @commands.command(name="status")
    async def status(self, ctx, membro: discord.Member = None):
        """Exibe o status do personagem do usuário ou de outro jogador."""
        if membro is None:
            membro = ctx.author

        jogador = obter_status(membro.id, ctx.guild.id)

        if jogador is None:
            embed = discord.Embed(
                title="| Erro",
                description=(
                    f"**{membro.mention} "
                    "não possui um personagem registrado.**"
                ),
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=membro.display_avatar.url)
            embed.set_footer(text="Tensura Moon - Korczak Technologies!")
            await ctx.send(embed=embed)
            return

        # Dados do personagem
        nome = jogador.get("Nome", "Não definido")
        raca = jogador.get("Raça", "Não definida")
        nivel = jogador.get("Nivel", 0)
        xp = jogador.get("XP", 0)
        forca = jogador.get("Força", 0)
        defesa = jogador.get("Defesa", 0)
        velocidade = jogador.get("Velocidade", 0)
        destreza = jogador.get("Destreza", 0)
        magia = jogador.get("Magia", 0)
        sorte = jogador.get("Sorte", 0)
        vida = jogador.get("Vida", 0)
        vida_maxima = jogador.get("Vida_Maxima", 0)
        mana = jogador.get("Mana", 0)
        mana_maxima = jogador.get("Mana Total", 0)

        # Criar embed
        avatar = ctx.author.display_avatar
        embed = discord.Embed(
            title="📊 Status do Personagem",
            color=0x8B0000,
            timestamp=horario
        )
        embed.set_thumbnail(url=avatar)

        embed.add_field(
            name="👤 Personagem",
            value=(
                f"**Nome:** {nome}\n"
                f"**Raça:** {raca}\n"
                f"**Nível:** {nivel}\n"
                f"**XP:** {xp}"
            ),
            inline=False
        )

        embed.add_field(
            name="❤️ Vida",
            value=(
                f"`{barra_vida(vida, vida_maxima)}`\n"
                f"**{vida}/{vida_maxima}**"
            ),
            inline=False
        )

        embed.add_field(
            name="💧 Mana",
            value=(
                f"`{barra_mana(mana, mana_maxima)}`\n"
                f"**{mana}/{mana_maxima}**"
            ),
            inline=False
        )

        embed.add_field(
            name="✨ Magículas",
            value="**EM TESTE**",
            inline=False
        )

        embed.add_field(
            name="⚔️ Atributos",
            value=(
                f"**Força:** {forca}\n"
                f"**Defesa:** {defesa}\n"
                f"**Destreza:** {destreza}\n"
                f"**Velocidade:** {velocidade}\n"
                f"**Inteligência:** EM TESTE"
            ),
            inline=False
        )

        embed.set_footer(text="Tensura Moon - Korczak Technologies!")
        embed.set_image(
            url='https://discord.com/channels/1543039757146136586/1543040901251596288/1543768808664080465'
        )

        await ctx.send(embed=embed)

    # ==========================================
    # COMANDO REGISTRAR
    # ==========================================

    @commands.command(name="registrar")
    async def registrar(self, ctx):
        """Registra um personagem para um usuário pendente."""
        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)

        player = db["Jogadores"]
        jogador = player.find_one({"ID": user_id, "guild_id": guild_id})

        if jogador is None:
            await ctx.send(
                "❌ Você não possui uma ficha pendente. "
                "Contate um Administrador."
            )
            return

        if jogador.get("Situação") == "ativo":
            await ctx.send("❌ Você já está registrado.")
            return

        if jogador.get("Situação") != "pendente":
            await ctx.send(
                "❌ Sua ficha não está disponível para registro."
            )
            return

        # Sortear raça
        try:
            raca = sortear_raca()
            dados_raca = obter_dados_raca(raca)
        except Exception as erro:
            print(f"Erro ao carregar raças: {erro}")
            embed = discord.Embed(
                title="| Erro",
                description=(
                    "❌ **Não foi possível "
                    "carregar os dados das raças.**"
                ),
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            await ctx.send(embed=embed)
            return

        if dados_raca is None:
            await ctx.send(
                "❌ Erro: dados da raça não encontrados."
            )
            return

        # Sortear atributos
        atributos_base = {
            "Força": sortear_atributo(),
            "Defesa": sortear_atributo(),
            "Vitalidade": sortear_atributo(),
            "Velocidade": sortear_atributo(),
            "Destreza": sortear_atributo(),
            "Magia": sortear_atributo(),
            "Sorte": sortear_atributo()
        }

        # Aplicar bônus racial
        bonus = dados_raca.get("bonus", {})
        atributos = {}

        for atributo, valor in atributos_base.items():
            bonus_atributo = bonus.get(atributo, 0)
            atributos[atributo] = aplicar_bonus(valor, bonus_atributo)

        # Gerar magículas
        magiculas = random.randrange(0, 1001, 100)

        # Calcular vida
        vitalidade = atributos["Vitalidade"]
        vida_maxima = vitalidade * 10
        vida = vida_maxima

        # Calcular mana
        mana_maxima = magiculas * 0.1
        mana = mana_maxima

        # Atualizar ficha
        resultado = player.update_one(
            {
                "_id": jogador["_id"],
                "Situação": "pendente"
            },
            {
                "$set": {
                    "Raça": raca,
                    "Nivel": 1,
                    "XP": 0,
                    "Força": atributos["Força"],
                    "Defesa": atributos["Defesa"],
                    "Vitalidade": atributos["Vitalidade"],
                    "Velocidade": atributos["Velocidade"],
                    "Destreza": atributos["Destreza"],
                    "Magia": atributos["Magia"],
                    "Sorte": atributos["Sorte"],
                    "Magículas": magiculas,
                    "Vida": vida,
                    "Vida_Maxima": vida_maxima,
                    "Mana": mana,
                    "Mana Total": mana_maxima,
                    "Situação": "ativo"
                }
            }
        )

        if resultado.modified_count == 0:
            await ctx.send(
                "❌ Não foi possível registrar sua ficha. "
                "Ela pode já ter sido registrada."
            )
            return

        # Criar embed de sucesso
        embed = discord.Embed(
            title="| Registro concluído",
            description=(
                f"**{ctx.author.mention}**, "
                "seu personagem foi criado!"
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="🧬 Raça",
            value=f"**{raca}**",
            inline=False
        )

        embed.add_field(
            name="❤️ Vida",
            value=(
                f"`{barra_vida(vida, vida_maxima)}`\n"
                f"**{vida}/{vida_maxima}**"
            ),
            inline=False
        )

        embed.add_field(
            name="💧 Mana",
            value=(
                f"`{barra_mana(mana, mana_maxima)}`\n"
                f"**{mana}/{mana_maxima}**"
            ),
            inline=False
        )

        embed.add_field(
            name="✨ Magículas",
            value=f"**{magiculas}**",
            inline=False
        )

        embed.add_field(
            name="⚔️ Atributos",
            value=(
                f"**Força:** {atributos['Força']}\n"
                f"**Defesa:** {atributos['Defesa']}\n"
                f"**Vitalidade:** {atributos['Vitalidade']}\n"
                f"**Velocidade:** {atributos['Velocidade']}\n"
                f"**Destreza:** {atributos['Destreza']}\n"
                f"**Magia:** {atributos['Magia']}\n"
                f"**Sorte:** {atributos['Sorte']}"
            ),
            inline=False
        )

        embed.add_field(
            name="📊 Informações",
            value=(
                "**Nível:** 1\n"
                "**XP:** 0"
            ),
            inline=False
        )

        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Tensura Moon - Korczak Technologies!")

        await ctx.send(embed=embed)

    # ==========================================
    # COMANDO DESREGISTRAR
    # ==========================================

    @commands.command(name="desregistrar", aliases = ['desregist', 'dregistrar', 'dregist'])
    @commands.has_permissions(manage_roles=True)
    async def desregistrar(self, ctx, membro: discord.Member = None):
        """Desregistra um personagem (Admin)."""
        if membro is None:
            await ctx.send(
                "❌ Você precisa mencionar um jogador.\n"
                "Use: `!desregistrar @usuário`"
            )
            return

        player = db["Jogadores"]
        user_id = str(membro.id)
        guild_id = str(ctx.guild.id)

        jogador = player.find_one({
            "ID": user_id,
            "guild_id": guild_id
        })

        if jogador is None:
            await ctx.send(
                "❌ Esse usuário não possui uma ficha."
            )
            return

        if jogador.get("Situação") != "ativo":
            await ctx.send(
                "❌ Esse jogador não está registrado."
            )
            return

        # Desregistrar
        resultado = player.update_one(
            {
                "_id": jogador["_id"],
                "Situação": "ativo"
            },
            {
                "$set": {
                    "Nome": None,
                    "Raça": None,
                    "Nivel": 0,
                    "XP": 0,
                    "Força": 0,
                    "Defesa": 0,
                    "Velocidade": 0,
                    "Destreza": 0,
                    "Magia": 0,
                    "Sorte": 0,
                    "Situação": "pendente"
                }
            }
        )

        if resultado.modified_count == 0:
            await ctx.send(
                "❌ Não foi possível desregistrar "
                "esse jogador."
            )
            return

        # Embed de sucesso
        embed = discord.Embed(
            title="| Jogador desregistrado",
            description=(
                f"**{membro.mention}** foi "
                "desregistrado com sucesso."
            ),
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="📋 Situação",
            value="**Pendente**",
            inline=False
        )

        embed.add_field(
            name="👤 Registrador",
            value=ctx.author.mention,
            inline=False
        )

        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.set_footer(text="Tensura Moon - Korczak Technologies!")

        await ctx.send(embed=embed)

    @commands.command(name='habilidades', aliases = ["habs", "skills"])

# ==========================================
# SETUP
# ==========================================

async def setup(bot):
    """Função de setup do cog."""
    await bot.add_cog(Status(bot))
