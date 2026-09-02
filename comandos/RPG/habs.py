import discord
from discord.ext import commands
from database.python.mongodb import db
import json
import os


# ======================================================
# CONFIGURAÇÕES
# ======================================================

ORDEM_RARIDADES = [
    "Comum",
    "Única",
    "Raça",
    "Definitiva",
    "Suprema",
    "Extra"
]


ARQUIVOS_HABILIDADES = {
    "Comum": "database/json/habilidades/habs_comuns.json",
    "Única": "database/json/habilidades/habs_unicas.json",
    "Raça": "database/json/habilidades/habs_raca.json",
    "Definitiva": "database/json/habilidades/habs_definitivas.json",
    "Suprema": "database/json/habilidades/habs_supremas.json",
    "Extra": "database/json/habilidades/habs_extras.json"
}


ARQUIVO_RACAS = "database/json/racas.json"


RARIDADE_MAP = {
    "comum": "Comum",
    "única": "Única",
    "unica": "Única",
    "raça": "Raça",
    "raca": "Raça",
    "definitiva": "Definitiva",
    "suprema": "Suprema",
    "extra": "Extra"
}


COR_RARIDADE = {
    "Comum": 0x95a5a6,
    "Única": 0x3498db,
    "Raça": 0x2ecc71,
    "Definitiva": 0x9b59b6,
    "Suprema": 0xe67e22,
    "Extra": 0xe74c3c,
}


# ======================================================
# COG
# ======================================================

class Habilidades(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.cache_habilidades = (
            self._carregar_habilidades()
        )

        print(
            f"✅ Total no cache: "
            f"{len(self.cache_habilidades)} habilidades"
        )


    # ==================================================
    # CARREGAR HABILIDADES
    # ==================================================

    def _carregar_habilidades(self):

        habilidades_cache = {}

        for raridade, arquivo in ARQUIVOS_HABILIDADES.items():

            try:

                if not os.path.exists(arquivo):

                    print(
                        f"❌ Arquivo não existe: {arquivo}"
                    )

                    continue


                print(
                    f"📂 Lendo: {arquivo}"
                )


                with open(
                    arquivo,
                    "r",
                    encoding="utf-8"
                ) as f:

                    dados = json.load(f)


                print(
                    f"  ✅ {len(dados)} habilidades "
                    f"encontradas em {raridade}"
                )


                for hab in dados:

                    hab_id = str(
                        hab.get("ID", "")
                    ).strip()


                    if not hab_id:

                        print(
                            f"⚠️ Habilidade sem ID: {hab}"
                        )

                        continue


                    raridade_raw = str(
                        hab.get(
                            "raridade",
                            ""
                        )
                    ).lower()


                    raridade_corrigida = (
                        RARIDADE_MAP.get(
                            raridade_raw,
                            raridade
                        )
                    )


                    habilidades_cache[hab_id] = {

                        "id": hab_id,

                        "nome": hab.get(
                            "nome",
                            "Desconhecido"
                        ),

                        "raridade": raridade_corrigida,

                        "descricao": hab.get(
                            "descricao",
                            ""
                        ),

                        "tipo": hab.get(
                            "tipo",
                            ""
                        ),

                        "elemento": hab.get(
                            "elemento",
                            None
                        ),

                        "passiva": hab.get(
                            "passiva",
                            "nao"
                        ),

                        "ativa": hab.get(
                            "ativa",
                            "nao"
                        ),

                        "bonus": hab.get(
                            "bonus",
                            {}
                        ),

                        "hab_ativa": hab.get(
                            "hab_ativa",
                            ""
                        )
                    }


            except FileNotFoundError:

                print(
                    f"❌ Arquivo não encontrado: "
                    f"{arquivo}"
                )


            except json.JSONDecodeError as e:

                print(
                    f"❌ Erro ao ler JSON "
                    f"{arquivo}: {e}"
                )


            except Exception as e:

                print(
                    f"❌ Erro inesperado "
                    f"em {arquivo}: {e}"
                )


        return habilidades_cache


    # ==================================================
    # BUSCAR HABILIDADE
    # ==================================================

    def _buscar_habilidade(
        self,
        hab_id
    ):

        hab_id = (
            str(hab_id)
            .strip()
            .strip('"')
            .strip("'")
        )

        return self.cache_habilidades.get(
            hab_id
        )


    # ==================================================
    # PARSE DAS HABILIDADES
    # ==================================================

    def _parse_habilidades(
        self,
        habilidades_raw
    ):

        if not habilidades_raw:

            return []


        if isinstance(
            habilidades_raw,
            list
        ):

            ids = []


            for item in habilidades_raw:

                if isinstance(
                    item,
                    str
                ):

                    if "," in item:

                        ids.extend(
                            [
                                i.strip()
                                .strip('"')
                                .strip("'")

                                for i in item.split(",")

                                if i.strip()
                            ]
                        )

                    else:

                        ids.append(
                            item
                            .strip()
                            .strip('"')
                            .strip("'")
                        )

                else:

                    ids.append(
                        str(item)
                        .strip()
                        .strip('"')
                        .strip("'")
                    )


            return [
                hab_id
                for hab_id in ids
                if hab_id
            ]


        if isinstance(
            habilidades_raw,
            str
        ):

            limpa = (
                habilidades_raw
                .replace("[", "")
                .replace("]", "")
                .replace('"', "")
                .replace("'", "")
            )


            return [
                hab_id.strip()

                for hab_id in limpa.split(",")

                if hab_id.strip()
            ]


        return []


    # ==================================================
    # !HABILIDADES
    # ==================================================

    @commands.command(
        name="habilidades",
        aliases=[
            "habs",
            "habils",
            "skills"
        ]
    )
    async def habs(
        self,
        ctx
    ):

        if db is None:

            await ctx.send(
                "❌ Banco de dados não conectado."
            )

            return


        if ctx.guild is None:

            await ctx.send(
                "❌ Este comando só pode ser usado "
                "em um servidor."
            )

            return


        habilidades_collection = db[
            "Habilidades"
        ]


        doc_habilidades = (
            habilidades_collection.find_one({
                "ID": str(ctx.author.id),
                "guild_id": str(ctx.guild.id)
            })
        )


        if not doc_habilidades:

            await ctx.send(
                "❌ Você não possui "
                "habilidades registradas."
            )

            return


        if not doc_habilidades.get(
            "habilidades"
        ):

            await ctx.send(
                "❌ Você ainda não possui "
                "nenhuma habilidade."
            )

            return


        ids_do_jogador = (
            self._parse_habilidades(
                doc_habilidades["habilidades"]
            )
        )


        if not ids_do_jogador:

            await ctx.send(
                "❌ Você ainda não possui "
                "nenhuma habilidade."
            )

            return


        habilidades_encontradas = []

        ids_nao_encontrados = []


        for hab_id in ids_do_jogador:

            hab = self._buscar_habilidade(
                hab_id
            )


            if hab:

                habilidades_encontradas.append(
                    hab
                )

            else:

                ids_nao_encontrados.append(
                    hab_id
                )


        if not habilidades_encontradas:

            await ctx.send(
                "❌ Nenhuma habilidade encontrada "
                "no catálogo.\n"
                f"IDs: "
                f"{', '.join(ids_nao_encontrados[:5])}"
            )

            return


        # ==============================================
        # AGRUPAR POR RARIDADE
        # ==============================================

        agrupado = {}


        for hab in habilidades_encontradas:

            raridade = hab.get(
                "raridade",
                "Outras"
            )


            agrupado.setdefault(
                raridade,
                []
            ).append(
                hab
            )


        # ==============================================
        # CRIAR EMBED
        # ==============================================

        embed = discord.Embed(
            title=(
                "📖 Catálogo de Habilidades — "
                f"{ctx.author.display_name}"
            ),
            color=discord.Color.blurple()
        )


        embed.set_thumbnail(
            url=ctx.author.display_avatar.url
        )


        raridades_presentes = list(
            agrupado.keys()
        )


        ordem_final = (

            [
                r

                for r in ORDEM_RARIDADES

                if r in agrupado
            ]

            +

            [
                r

                for r in raridades_presentes

                if r not in ORDEM_RARIDADES
            ]

        )


        for raridade in ordem_final:

            lista = agrupado[raridade]


            texto = "\n".join(

                f"`{h['id']}` **{h['nome']}**"

                for h in lista

            )


            if len(texto) > 1024:

                texto = (
                    texto[:1000]
                    + "\n... (lista truncada)"
                )


            embed.add_field(
                name=(
                    f"{raridade} "
                    f"({len(lista)})"
                ),
                value=texto,
                inline=False
            )


        if ids_nao_encontrados:

            texto_ids = ", ".join(
                ids_nao_encontrados[:10]
            )


            if len(
                ids_nao_encontrados
            ) > 10:

                texto_ids += "..."


            embed.add_field(
                name="⚠️ IDs não encontrados",
                value=texto_ids,
                inline=False
            )


        embed.set_footer(
            text=(
                "Total de habilidades: "
                f"{len(habilidades_encontradas)}"
            )
        )


        await ctx.send(
            embed=embed
        )


    # ==================================================
    # CARREGAR RAÇAS
    # ==================================================

    def _carregar_racas(self):

        try:

            if not os.path.exists(
                ARQUIVO_RACAS
            ):

                print(
                    "❌ Arquivo de raças não encontrado: "
                    f"{ARQUIVO_RACAS}"
                )

                return []


            with open(
                ARQUIVO_RACAS,
                "r",
                encoding="utf-8"
            ) as f:

                dados = json.load(f)


            # ------------------------------------------
            # FORMATO:
            # [
            #   "Humano",
            #   "Slime"
            # ]
            # ------------------------------------------

            if isinstance(
                dados,
                list
            ):

                return dados


            # ------------------------------------------
            # FORMATO:
            # {
            #   "racas": [...]
            # }
            # ------------------------------------------

            if isinstance(
                dados,
                dict
            ):

                racas = dados.get(
                    "racas"
                )


                if isinstance(
                    racas,
                    list
                ):

                    return racas


                # Se as raças forem diretamente
                # as chaves do objeto.

                return list(
                    dados.keys()
                )


            return []


        except json.JSONDecodeError as e:

            print(
                f"❌ Erro ao ler racas.json: {e}"
            )

            return []


        except Exception as e:

            print(
                f"❌ Erro ao carregar raças: {e}"
            )

            return []


    # ==================================================
    # !RACAS
    # ==================================================

    @commands.command(
        name="racas",
        aliases=[
            "raças",
            "race",
            "raca",
            "raça"
        ]
    )
    async def racas(
        self,
        ctx
    ):
        """
        Lista todas as raças disponíveis
        no servidor.
        """

        racas_disponiveis = (
            self._carregar_racas()
        )


        if not racas_disponiveis:

            await ctx.send(
                "❌ Nenhuma raça foi encontrada em "
                "`database/racas.json`."
            )

            return


        lista_racas = []


        for indice, raca in enumerate(
            racas_disponiveis,
            start=1
        ):

            # ------------------------------------------
            # RAÇA COMO OBJETO
            # ------------------------------------------

            if isinstance(
                raca,
                dict
            ):

                nome = (

                    raca.get("nome")

                    or raca.get("Nome")

                    or raca.get("id")

                    or raca.get("ID")

                    or "Desconhecida"

                )


            # ------------------------------------------
            # RAÇA COMO STRING
            # ------------------------------------------

            else:

                nome = str(
                    raca
                )


            lista_racas.append(
                f"**{indice}.** {nome}"
            )


        # ==============================================
        # CRIAR EMBEDS
        # ==============================================

        embeds = []

        parte_atual = ""


        for linha in lista_racas:

            nova_linha = (
                linha + "\n"
            )


            if (

                len(parte_atual)
                + len(nova_linha)

                > 4000

            ):

                embed = discord.Embed(
                    title="🧬 Raças Disponíveis",
                    description=parte_atual,
                    color=discord.Color.green()
                )


                embeds.append(
                    embed
                )


                parte_atual = nova_linha


            else:

                parte_atual += nova_linha


        if parte_atual:

            embed = discord.Embed(
                title="🧬 Raças Disponíveis",
                description=parte_atual,
                color=discord.Color.green()
            )


            embeds.append(
                embed
            )


        # ==============================================
        # RODAPÉ E PÁGINAS
        # ==============================================

        total_racas = len(
            lista_racas
        )


        total_paginas = len(
            embeds
        )


        for indice, embed in enumerate(
            embeds,
            start=1
        ):

            embed.set_footer(
                text=(
                    f"Total: {total_racas} raça(s) "
                    f"• Página "
                    f"{indice}/{total_paginas}"
                )
            )


            await ctx.send(
                embed=embed
            )


    # ==================================================
    # COMANDO DE TESTE
    # ==================================================

    @commands.command(
        name="testhabilidades"
    )
    async def testhabilidades(
        self,
        ctx
    ):

        if db is None:

            await ctx.send(
                "❌ Banco não conectado."
            )

            return


        habilidades_collection = db[
            "Habilidades"
        ]


        doc = (
            habilidades_collection.find_one({
                "ID": str(ctx.author.id),
                "guild_id": str(ctx.guild.id)
            })
        )


        if not doc:

            await ctx.send(
                "❌ Documento não encontrado "
                "na coleção Habilidades."
            )

            return


        texto = (
            "**Documento na coleção Habilidades:**\n"
            "```json\n"
            f"{json.dumps(doc, indent=2, default=str)[:1900]}"
            "\n```"
        )


        await ctx.send(
            texto
        )


# ======================================================
# SETUP
# ======================================================

async def setup(bot):

    await bot.add_cog(
        Habilidades(bot)
    )