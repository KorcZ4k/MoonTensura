import discord
import json
import random

from pathlib import Path
from discord.ext import commands

from comandos.RPG.barra_status import barra_mana, barra_vida
from database.python.status import (
    obter_status
)

from database.python.mongodb import db


# ==========================================
# COLLECTION
# ==========================================

jogadores = db["Jogadores"]


# ==========================================
# CAMINHO DOS DADOS
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

RACAS_FILE = BASE_DIR / "database" / "json" / "racas.json"


# ==========================================
# CARREGAR RAÇAS
# ==========================================
def carregar_racas():

    with open(
        RACAS_FILE,
        "r",
        encoding="utf-8"
    ) as arquivo:

        dados = json.load(arquivo)

    return dados["racas"]


# ==========================================
# SORTEAR RAÇA
# ==========================================

def sortear_raca():

    racas = carregar_racas()

    nomes = []
    pesos = []

    for raca in racas:

        nomes.append(
            raca["nome"]
        )

        pesos.append(
            raca["chance"]
        )

    return random.choices(
        nomes,
        weights=pesos,
        k=1
    )[0]


# ==========================================
# OBTER DADOS DA RAÇA
# ==========================================

def obter_dados_raca(
    nome_raca
):

    racas = carregar_racas()

    for raca in racas:

        if raca["nome"] == nome_raca:

            return raca

    return None


# ==========================================
# SORTEAR ATRIBUTO
# ==========================================

def sortear_atributo():

    faixa = random.choice(
        [
            "crianca",
            "muito_fraco",
            "fraco",
            "normal",
            "forte"
        ]
    )


    if faixa == "crianca":

        return random.randint(
            0,
            50
        )


    if faixa == "muito_fraco":

        return random.randint(
            50,
            80
        )


    if faixa == "fraco":

        return random.randint(
            80,
            90
        )


    if faixa == "normal":

        return random.randint(
            90,
            110
        )


    if faixa == "forte":

        return random.randint(
            110,
            130
        )


# ==========================================
# APLICAR BÔNUS RACIAL
# ==========================================

def aplicar_bonus(
    valor,
    bonus
):

    return int(
        valor * (1 + bonus)
    )


# ==========================================
# COG STATUS
# ==========================================

class Status(commands.Cog):


    def __init__(
        self,
        bot
    ):

        self.bot = bot


    # ==========================================
    # COMANDO STATUS
    # ==========================================

    @commands.command(
        name="status"
    )
    async def status(
        self,
        ctx,
        membro: discord.Member = None
    ):

        if membro is None:

            membro = ctx.author


        jogador = obter_status(
            membro.id,
            ctx.guild.id
        )


        # ======================================
        # JOGADOR NÃO ENCONTRADO
        # ======================================

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

            embed.set_thumbnail(
                url=membro.display_avatar.url
            )

            embed.set_footer(
                text="Tensura Moon - Korczak Technologies!"
            )

            await ctx.send(
                embed=embed
            )

            return


        # ======================================
        # DADOS
        # ======================================

        nome = jogador.get(
            "Nome",
            "Não definido"
        )

        raca = jogador.get(
            "Raça",
            "Não definida"
        )

        nivel = jogador.get(
            "Nivel",
            0
        )

        xp = jogador.get(
            "XP",
            0
        )

        forca = jogador.get(
            "Força",
            0
        )

        defesa = jogador.get(
            "Defesa",
            0
        )

        velocidade = jogador.get(
            "Velocidade",
            0
        )

        destreza = jogador.get(
            "Destreza",
            0
        )

        magia = jogador.get(
            "Magia",
            0
        )

        sorte = jogador.get(
            "Sorte",
            0
        )
        vida = jogador.get(
            "Vida",
            0
        )
        vida_maxima = jogador.get(
            "Vida_Maxima",
            0
        )
        mana = jogador.get(
            "Mana",
            0
        )
        mana_maxima = jogador.get(
            "Mana Total",
            0
        )

        # ======================================
        # EMBED
        # ======================================

        embed = discord.Embed(
    title="📊 Status do Personagem",
    color=0x8B0000
    )

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
    value=f"**EM TESTE**",
    inline=False
    )

        embed.add_field(
    name="⚔️ Atributos",
    value=(
        f"**Força:** {forca}\n"
        f"**Defesa:** {defesa}\n"
        f"**Agilidade:** {agilidade}\n"
        f"**Velocidade:** {velocidade}\n"
        f"**Inteligência:** {inteligencia}"
    ),
    inline=False
    )

        embed.set_footer(
    text="Tensura Moon • Korczak Technologies!"
    )


        await ctx.send(
            embed=embed
        )


    # ==========================================
    # COMANDO REGISTRAR
    # ==========================================
    @commands.command(name="registrar")
    async def registrar(self, ctx):

        user_id = str(ctx.author.id)

        guild_id = str(
        ctx.guild.id
        )
        player = db["Jogadores"]
        jogador = player.find_one({
            "ID": user_id,
            "guild_id": guild_id
        })
        if jogador is None:
            await ctx.send(
            "❌ Você não possui uma ficha pendente. "
            "Contate um Administrador."
        )

            return


        # ======================================
        # JÁ REGISTRADO
        # ======================================

        if jogador.get("Situação") == "ativo":

            await ctx.send(
            "❌ Você já está registrado."
        )

            return


        # ======================================
        # SITUAÇÃO INVÁLIDA
        # ======================================

        if jogador.get("Situação") != "pendente":

            await ctx.send(
            "❌ Sua ficha não está disponível para registro."
        )

            return


        # ======================================
        # SORTEAR RAÇA
        # ======================================

        try:

            raca = sortear_raca()

            dados_raca = obter_dados_raca(
            raca
        )

        except Exception as erro:

            print(
                f"Erro ao carregar raças: {erro}"
            )

            embed = discord.Embed(
                title="| Erro",
                description=(
                    "❌ **Não foi possível "
                    "carregar os dados das raças.**"
                ),
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )

            await ctx.send(
                embed=embed
            )

            return


        # ======================================
        # RAÇA NÃO ENCONTRADA
        # ======================================

        if dados_raca is None:

            await ctx.send(
                "❌ Erro: dados da raça não encontrados."
            )

            return


        # ======================================
        # SORTEAR ATRIBUTOS
        # ======================================

        atributos_base = {

            "Força":
                sortear_atributo(),

            "Defesa":
                sortear_atributo(),

            "Velocidade":
                sortear_atributo(),

            "Destreza":
                sortear_atributo(),

            "Magia":
                sortear_atributo(),

            "Sorte":
                sortear_atributo()
        }


        # ======================================
        # APLICAR BÔNUS RACIAL
        # ======================================

        bonus = dados_raca.get(
            "bonus",
            {}
        )


        atributos = {}


        for atributo, valor in atributos_base.items():

            bonus_atributo = bonus.get(
                atributo,
                0
            )

            atributos[atributo] = aplicar_bonus(
                valor,
                bonus_atributo
            )


        # ======================================
        # ATUALIZAR FICHA
        # ======================================

        resultado = player.update_one(

            {
                "_id": jogador["_id"],
                "Situação": "pendente"
            },

            {
                "$set": {

                    "Raça":
                        raca,

                    "Nivel":
                        1,

                    "XP":
                        0,

                    "Força":
                        atributos["Força"],

                    "Defesa":
                        atributos["Defesa"],

                    "Velocidade":
                        atributos["Velocidade"],

                    "Destreza":
                        atributos["Destreza"],

                    "Magia":
                        atributos["Magia"],

                    "Sorte":
                        atributos["Sorte"],

                    "Situação":
                        "ativo"
                }
            }
        )
        # ======================================
        # VERIFICAR ATUALIZAÇÃO
        # ======================================

        if resultado.modified_count == 0:

            await ctx.send(
                "❌ Não foi possível registrar sua ficha. "
                "Ela pode já ter sido registrada."
            )

            return


        # ======================================
        # EMBED
        # ======================================

        embed = discord.Embed(

            title="| Registro concluído",

            description=(
                f"**{ctx.author.mention}**, "
                "seu personagem foi criado!"
            ),

            color=discord.Color.green(),

            timestamp=discord.utils.utcnow()
        )


        # ======================================
        # RAÇA
        # ======================================

        embed.add_field(

            name="🧬 Raça",

            value=f"**{raca}**",

            inline=False
        )


        # ======================================
        # ATRIBUTOS
        # ======================================

        embed.add_field(

            name="⚔️ Atributos",

            value=(

                f"**Força:** "
                f"{atributos['Força']}\n"

                f"**Defesa:** "
                f"{atributos['Defesa']}\n"

                f"**Velocidade:** "
                f"{atributos['Velocidade']}\n"

                f"**Destreza:** "
                f"{atributos['Destreza']}\n"

                f"**Magia:** "
                f"{atributos['Magia']}\n"

                f"**Sorte:** "
                f"{atributos['Sorte']}"
            ),

            inline=False
        )


        # ======================================
        # INFORMAÇÕES
        # ======================================

        embed.add_field(

            name="📊 Informações",

            value=(

                "**Nível:** 1\n"
                "**XP:** 0"
            ),

            inline=False
        )


        # ======================================
        # AVATAR
        # ======================================

        embed.set_thumbnail(

            url=ctx.author.display_avatar.url
        )


        # ======================================
        # FOOTER
        # ======================================

        embed.set_footer(

            text="Tensura Moon - Korczak Technologies!"
        )


        # ======================================
        # ENVIAR
        # ======================================

        await ctx.send(
            embed=embed
        )
    
    @commands.command(
        name="desregistrar"
    )
    @commands.has_permissions(manage_roles=True)
    async def desregistrar(
        self,
        ctx,
        membro: discord.Member = None
    ):
        # ======================================
        # VERIFICAR MENÇÃO
        # ======================================

        if membro is None:

            await ctx.send(
                "❌ Você precisa mencionar um jogador.\n"
                "Use: `!desregistrar @usuário`"
            )

            return


        # ======================================
        # IMPEDIR DESREGISTRAR A SI MESMO
        # ======================================


        # ======================================
        # COLLECTION
        # ======================================

        player = db["Jogadores"]


        user_id = str(
            membro.id
        )

        guild_id = str(
            ctx.guild.id
        )


        # ======================================
        # BUSCAR JOGADOR
        # ======================================

        jogador = player.find_one({

            "ID": user_id,

            "guild_id": guild_id
        })


        # ======================================
        # JOGADOR NÃO ENCONTRADO
        # ======================================

        if jogador is None:

            await ctx.send(
                "❌ Esse usuário não possui uma ficha."
            )

            return


        # ======================================
        # VERIFICAR SITUAÇÃO
        # ======================================

        if jogador.get("Situação") != "ativo":

            await ctx.send(
                "❌ Esse jogador não está registrado."
            )

            return


        # ======================================
        # DESREGISTRAR
        # ======================================

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


        # ======================================
        # VERIFICAR ATUALIZAÇÃO
        # ======================================

        if resultado.modified_count == 0:

            await ctx.send(
                "❌ Não foi possível desregistrar "
                "esse jogador."
            )

            return


        # ======================================
        # EMBED
        # ======================================

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


        embed.set_thumbnail(

            url=membro.display_avatar.url
        )


        embed.set_footer(

            text="Tensura Moon - Korczak Technologies!"
        )


        await ctx.send(
            embed=embed
        )





# ==========================================
# SETUP
# ==========================================

async def setup(
    bot
):

    await bot.add_cog(
        Status(bot)
    )
