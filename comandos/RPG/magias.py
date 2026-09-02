import discord
from discord.ext import commands

from database.python.mongodb import db
from database.python.magias import DatabaseMagias


class Magias(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # ============================================================
    # FUNÇÕES AUXILIARES
    # ============================================================

    def normalizar(self, texto):
        """
        Normaliza um texto para comparação.
        Remove espaços extras e converte para minúsculo.
        """
        if texto is None:
            return ""

        return str(texto).strip().lower()

    def normalizar_lista(self, lista):
        """
        Normaliza uma lista de strings ou dicionários.
        """

        resultado = []

        if not lista:
            return resultado

        for item in lista:

            if isinstance(item, dict):
                valor = (
                    item.get("id")
                    or item.get("ID")
                    or item.get("nome")
                    or item.get("Nome")
                    or ""
                )
            else:
                valor = item

            resultado.append(
                self.normalizar(valor)
            )

        return resultado

    def carregar_catalogo(self, dados, chave):
        """
        Obtém uma lista de um catálogo JSON.

        Exemplo:
        {
            "formas": [...]
        }

        ou:
        {
            "elementos": [...]
        }
        """

        if not dados:
            return []

        if isinstance(dados, list):
            return dados

        if isinstance(dados, dict):
            resultado = dados.get(chave, [])

            if isinstance(resultado, list):
                return resultado

        return []

    def buscar_item(self, lista, identificador):
        """
        Busca um item pelo ID ou pelo nome.
        """

        identificador = self.normalizar(identificador)

        for item in lista:

            if isinstance(item, dict):

                item_id = self.normalizar(
                    item.get("id")
                    or item.get("ID")
                    or ""
                )

                item_nome = self.normalizar(
                    item.get("nome")
                    or item.get("Nome")
                    or ""
                )

                if identificador == item_id:
                    return item

                if identificador == item_nome:
                    return item

            else:

                if self.normalizar(item) == identificador:
                    return item

        return None

    def formatar_lista(self, lista, limite=1024):
        """
        Formata uma lista para um Embed.
        """

        if not lista:
            return "Nenhum."

        texto = ""

        for item in lista:

            if isinstance(item, dict):

                nome = (
                    item.get("nome")
                    or item.get("Nome")
                    or item.get("id")
                    or item.get("ID")
                    or "Desconhecido"
                )

                item_id = (
                    item.get("id")
                    or item.get("ID")
                    or ""
                )

                if item_id:
                    linha = f"• **{nome}** (`{item_id}`)\n"
                else:
                    linha = f"• **{nome}**\n"

            else:

                linha = f"• `{item}`\n"

            if len(texto) + len(linha) > limite:
                texto += "..."
                break

            texto += linha

        return texto or "Nenhum."

    # ============================================================
    # COMANDO BASE
    # ============================================================

    @commands.group(
        name="magias",
        aliases=["magia"],
        invoke_without_command=True
    )
    async def magias(self, ctx):

        embed = discord.Embed(
            title="🔮 Sistema de Magias",
            description=(
                "`!magias list` — Ver suas formas e elementos\n"
                "`!magias formas` — Ver todas as formas disponíveis\n"
                "`!magias elementos` — Ver todos os elementos disponíveis\n"
                "`!magias count` — Ver quantidade de formas\n\n"
                "`!usarmagia <forma> <elemento>` — Usar uma magia"
            ),
            color=discord.Color.purple()
        )

        await ctx.send(embed=embed)

    # ============================================================
    # !MAGIAS LIST
    # ============================================================

    @magias.command(
        name="list",
        aliases=["lista", "listar"]
    )
    async def listar_magias(self, ctx):

        if ctx.guild is None:
            await ctx.send(
                "❌ Este comando só pode ser usado em um servidor."
            )
            return

        if db is None:
            await ctx.send(
                "❌ Banco de dados não conectado."
            )
            return

        db_magias = DatabaseMagias(db)

        doc = db_magias.get_magia_doc(
            str(ctx.author.id),
            str(ctx.guild.id)
        )

        if not doc:
            await ctx.send(
                "❌ Você não possui um documento de magias registrado."
            )
            return

        # ========================================================
        # ESTRUTURA CORRETA:
        #
        # magias = FORMAS
        # tipos = ELEMENTOS
        # ========================================================

        formas = doc.get("magias", [])
        elementos = doc.get("tipos", [])

        embed = discord.Embed(
            title=f"🔮 Magias de {ctx.author.display_name}",
            color=discord.Color.purple()
        )

        embed.set_thumbnail(
            url=ctx.author.display_avatar.url
        )

        # --------------------------------------------------------
        # FORMAS
        # --------------------------------------------------------

        if formas:

            texto_formas = self.formatar_lista(
                formas
            )

            embed.add_field(
                name=f"🔷 Formas ({len(formas)})",
                value=texto_formas,
                inline=False
            )

        else:

            embed.add_field(
                name="🔷 Formas (0)",
                value="Você não possui nenhuma forma.",
                inline=False
            )

        # --------------------------------------------------------
        # ELEMENTOS
        # --------------------------------------------------------

        if elementos:

            texto_elementos = self.formatar_lista(
                elementos
            )

            embed.add_field(
                name=f"🌈 Elementos ({len(elementos)})",
                value=texto_elementos,
                inline=False
            )

        else:

            embed.add_field(
                name="🌈 Elementos (0)",
                value="Você não possui nenhum elemento.",
                inline=False
            )

        embed.set_footer(
            text="Use: !usarmagia <forma> <elemento>"
        )

        await ctx.send(embed=embed)

    # ============================================================
    # !MAGIAS COUNT
    # ============================================================

    @magias.command(
        name="count",
        aliases=["contar", "quantidade"]
    )
    async def contar_magias(self, ctx):

        if ctx.guild is None:
            await ctx.send(
                "❌ Este comando só pode ser usado em um servidor."
            )
            return

        if db is None:
            await ctx.send(
                "❌ Banco de dados não conectado."
            )
            return

        db_magias = DatabaseMagias(db)

        doc = db_magias.get_magia_doc(
            str(ctx.author.id),
            str(ctx.guild.id)
        )

        if not doc:
            await ctx.send(
                "❌ Você não possui magias registradas."
            )
            return

        # magias = FORMAS
        formas = doc.get("magias", [])

        await ctx.send(
            f"🔷 {ctx.author.mention}, você possui "
            f"**{len(formas)} forma(s)**."
        )

    # ============================================================
    # !MAGIAS FORMAS
    # ============================================================

    @magias.command(
        name="formas",
        aliases=["forma"]
    )
    async def listar_formas(self, ctx):

        if db is None:
            await ctx.send(
                "❌ Banco de dados não conectado."
            )
            return

        db_magias = DatabaseMagias(db)

        # Carrega:
        # database/json/magias/formas.json
        dados = db_magias._carregar_json(
            db_magias.arquivo_formas
        )

        formas = self.carregar_catalogo(
            dados,
            "formas"
        )

        if not formas:
            await ctx.send(
                "❌ Nenhuma forma foi encontrada no "
                "`database/json/magias/formas.json`."
            )
            return

        embed = discord.Embed(
            title="🔷 Formas de Magia",
            description=(
                "Todas as formas disponíveis no sistema."
            ),
            color=discord.Color.purple()
        )

        paginas = []
        pagina_atual = ""

        for forma in formas:

            if not isinstance(forma, dict):
                linha = f"• `{forma}`\n"

            else:

                forma_id = forma.get(
                    "id",
                    "desconhecida"
                )

                nome = forma.get(
                    "nome",
                    forma_id
                )

                descricao = forma.get(
                    "descricao",
                    "Sem descrição."
                )

                mana = forma.get(
                    "mana_base",
                    0
                )

                dano = forma.get(
                    "dano_base",
                    0
                )

                linha = (
                    f"**{nome}** (`{forma_id}`)\n"
                    f"└ {descricao}\n"
                    f"└ 💠 Mana: `{mana}` | "
                    f"⚔️ Dano: `{dano}`\n\n"
                )

            if len(pagina_atual) + len(linha) > 1024:

                paginas.append(
                    pagina_atual
                )

                pagina_atual = ""

            pagina_atual += linha

        if pagina_atual:
            paginas.append(pagina_atual)

        for indice, pagina in enumerate(
            paginas,
            start=1
        ):

            nome_campo = (
                "📜 Formas"
                if len(paginas) == 1
                else f"📜 Formas — Página {indice}"
            )

            embed.add_field(
                name=nome_campo,
                value=pagina,
                inline=False
            )

        embed.set_footer(
            text=f"Total: {len(formas)} forma(s)"
        )

        await ctx.send(embed=embed)

    # ============================================================
    # !MAGIAS ELEMENTOS
    # ============================================================

    @magias.command(
        name="elementos",
        aliases=["elemento"]
    )
    async def listar_elementos(self, ctx):

        if db is None:
            await ctx.send(
                "❌ Banco de dados não conectado."
            )
            return

        db_magias = DatabaseMagias(db)

        # Carrega:
        # database/json/magias/elementos.json
        dados = db_magias._carregar_json(
            db_magias.arquivo_elementos
        )

        elementos = self.carregar_catalogo(
            dados,
            "elementos"
        )

        if not elementos:
            await ctx.send(
                "❌ Nenhum elemento foi encontrado no "
                "`database/json/magias/elementos.json`."
            )
            return

        embed = discord.Embed(
            title="🌈 Elementos Mágicos",
            color=discord.Color.purple()
        )

        paginas = []
        pagina_atual = ""

        for elemento in elementos:

            if not isinstance(elemento, dict):

                linha = f"• `{elemento}`\n"

            else:

                elemento_id = elemento.get(
                    "id",
                    "desconhecido"
                )

                nome = elemento.get(
                    "nome",
                    elemento_id
                )

                descricao = elemento.get(
                    "descricao",
                    ""
                )

                linha = (
                    f"**{nome}** (`{elemento_id}`)"
                )

                if descricao:
                    linha += (
                        f"\n└ {descricao}"
                    )

                linha += "\n\n"

            if len(pagina_atual) + len(linha) > 1024:

                paginas.append(
                    pagina_atual
                )

                pagina_atual = ""

            pagina_atual += linha

        if pagina_atual:
            paginas.append(pagina_atual)

        for indice, pagina in enumerate(
            paginas,
            start=1
        ):

            nome_campo = (
                "📜 Elementos"
                if len(paginas) == 1
                else f"📜 Elementos — Página {indice}"
            )

            embed.add_field(
                name=nome_campo,
                value=pagina,
                inline=False
            )

        embed.set_footer(
            text=f"Total: {len(elementos)} elemento(s)"
        )

        await ctx.send(embed=embed)

    # ============================================================
    # !USARMAGIA <FORMA> <ELEMENTO>
    # ============================================================

    @commands.command(
        name="usarmagia",
        aliases=["usar_magia", "cast"]
    )
    async def usar_magia(
        self,
        ctx,
        forma_id: str,
        elemento_id: str
    ):

        """
        Exemplo:

        !usarmagia bola fogo

        O sistema:

        MongoDB:
            magias = FORMAS do jogador
            tipos = ELEMENTOS do jogador

        JSON:
            formas.json = dados da forma
            elementos.json = dados do elemento
        """

        if ctx.guild is None:
            await ctx.send(
                "❌ Este comando só pode ser usado em um servidor."
            )
            return

        if db is None:
            await ctx.send(
                "❌ Banco de dados não conectado."
            )
            return

        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)

        forma_id = self.normalizar(
            forma_id
        )

        elemento_id = self.normalizar(
            elemento_id
        )

        db_magias = DatabaseMagias(db)

        # ========================================================
        # BUSCA O DOCUMENTO DO JOGADOR
        # ========================================================

        doc = db_magias.get_magia_doc(
            user_id,
            guild_id
        )

        if not doc:

            await ctx.send(
                "❌ Você não possui um documento de magias registrado."
            )

            return

        # ========================================================
        # ESTRUTURA DO MONGODB
        #
        # "magias": [
        #     "bola",
        #     "raio"
        # ]
        #
        # "tipos": [
        #     "fogo"
        # ]
        # ========================================================

        formas_jogador = doc.get(
            "magias",
            []
        )

        elementos_jogador = doc.get(
            "tipos",
            []
        )

        # ========================================================
        # VERIFICA A FORMA
        # ========================================================

        formas_normalizadas = self.normalizar_lista(
            formas_jogador
        )

        if forma_id not in formas_normalizadas:

            await ctx.send(
                f"❌ Você não possui a forma "
                f"`{forma_id}`.\n\n"
                f"Use `!magias list` para ver suas formas."
            )

            return

        # ========================================================
        # VERIFICA O ELEMENTO
        # ========================================================

        elementos_normalizados = self.normalizar_lista(
            elementos_jogador
        )

        if elemento_id not in elementos_normalizados:

            await ctx.send(
                f"❌ Você não possui o elemento "
                f"`{elemento_id}`.\n\n"
                f"Use `!magias list` para ver seus elementos."
            )

            return

        # ========================================================
        # CARREGA FORMAS.JSON
        # ========================================================

        dados_formas = db_magias._carregar_json(
            db_magias.arquivo_formas
        )

        formas_catalogo = self.carregar_catalogo(
            dados_formas,
            "formas"
        )

        forma = self.buscar_item(
            formas_catalogo,
            forma_id
        )

        if not forma:

            await ctx.send(
                f"❌ A forma `{forma_id}` está no seu "
                f"MongoDB, mas não foi encontrada no "
                f"`formas.json`."
            )

            return

        # ========================================================
        # CARREGA ELEMENTOS.JSON
        # ========================================================

        dados_elementos = db_magias._carregar_json(
            db_magias.arquivo_elementos
        )

        elementos_catalogo = self.carregar_catalogo(
            dados_elementos,
            "elementos"
        )

        elemento = self.buscar_item(
            elementos_catalogo,
            elemento_id
        )

        if not elemento:

            await ctx.send(
                f"❌ O elemento `{elemento_id}` está no seu "
                f"MongoDB, mas não foi encontrado no "
                f"`elementos.json`."
            )

            return

        # ========================================================
        # DADOS DA FORMA
        # ========================================================

        forma_nome = forma.get(
            "nome",
            forma_id.title()
        )

        mana_base = forma.get(
            "mana_base",
            0
        )

        dano_base = forma.get(
            "dano_base",
            0
        )

        cura_base = forma.get(
            "cura_base",
            0
        )

        defesa_base = forma.get(
            "defesa_base",
            0
        )

        alcance = forma.get(
            "alcance",
            "Não definido"
        )

        alvo = forma.get(
            "alvo",
            "Não definido"
        )

        tipos_forma = forma.get(
            "tipos",
            []
        )

        efeito_forma = forma.get(
            "efeito",
            {}
        )

        # ========================================================
        # DADOS DO ELEMENTO
        # ========================================================

        elemento_nome = elemento.get(
            "nome",
            elemento_id.title()
        )

        # Os valores abaixo são opcionais e dependem
        # da estrutura do seu elementos.json.

        bonus_dano = elemento.get(
            "bonus_dano",
            elemento.get(
                "dano_bonus",
                0
            )
        )

        bonus_mana = elemento.get(
            "bonus_mana",
            elemento.get(
                "mana_bonus",
                0
            )
        )

        multiplicador_dano = elemento.get(
            "multiplicador_dano",
            1
        )

        efeito_elemento = elemento.get(
            "efeito",
            {}
        )

        # ========================================================
        # CÁLCULO DA MAGIA
        # ========================================================

        try:

            dano_final = (
                float(dano_base)
                + float(bonus_dano)
            ) * float(multiplicador_dano)

            if dano_final.is_integer():
                dano_final = int(
                    dano_final
                )

        except (
            ValueError,
            TypeError
        ):

            dano_final = dano_base

        try:

            mana_final = (
                float(mana_base)
                + float(bonus_mana)
            )

            if mana_final.is_integer():
                mana_final = int(
                    mana_final
                )

        except (
            ValueError,
            TypeError
        ):

            mana_final = mana_base

        # ========================================================
        # NOME FINAL
        # ========================================================

        nome_magia = (
            f"{forma_nome} de {elemento_nome}"
        )

        # ========================================================
        # EMBED
        # ========================================================

        embed = discord.Embed(
            title="✨ Magia Utilizada",
            description=(
                f"{ctx.author.mention} utilizou "
                f"**{nome_magia}**!"
            ),
            color=discord.Color.purple()
        )

        embed.add_field(
            name="🔷 Forma",
            value=forma_nome,
            inline=True
        )

        embed.add_field(
            name="🌈 Elemento",
            value=elemento_nome,
            inline=True
        )

        embed.add_field(
            name="💠 Mana Base",
            value=str(mana_final),
            inline=True
        )

        if dano_final > 0:

            embed.add_field(
                name="⚔️ Dano",
                value=str(dano_final),
                inline=True
            )

        if cura_base > 0:

            embed.add_field(
                name="💚 Cura",
                value=str(cura_base),
                inline=True
            )

        if defesa_base > 0:

            embed.add_field(
                name="🛡️ Defesa",
                value=str(defesa_base),
                inline=True
            )

        embed.add_field(
            name="🎯 Alvo",
            value=str(alvo),
            inline=True
        )

        embed.add_field(
            name="📏 Alcance",
            value=str(alcance),
            inline=True
        )

        # ========================================================
        # TIPOS DA FORMA
        # ========================================================

        if tipos_forma:

            embed.add_field(
                name="🏷️ Tipos",
                value=", ".join(
                    str(tipo)
                    for tipo in tipos_forma
                ),
                inline=False
            )

        # ========================================================
        # EFEITO DA FORMA
        # ========================================================

        if isinstance(
            efeito_forma,
            dict
        ) and efeito_forma:

            efeito_nome = efeito_forma.get(
                "nome",
                "Efeito"
            )

            efeito_descricao = efeito_forma.get(
                "descricao",
                ""
            )

            efeito_turnos = efeito_forma.get(
                "turnos",
                0
            )

            efeito_valor = efeito_forma.get(
                "valor",
                0
            )

            texto_efeito = (
                f"**{efeito_nome}**"
            )

            if efeito_descricao:

                texto_efeito += (
                    f"\n{efeito_descricao}"
                )

            if efeito_turnos:

                texto_efeito += (
                    f"\n⏱️ Duração: "
                    f"`{efeito_turnos}` turno(s)"
                )

            if efeito_valor:

                texto_efeito += (
                    f"\n📊 Valor: "
                    f"`{efeito_valor}`"
                )

            embed.add_field(
                name="✨ Efeito",
                value=texto_efeito,
                inline=False
            )

        # ========================================================
        # EFEITO DO ELEMENTO
        # ========================================================

        if isinstance(
            efeito_elemento,
            dict
        ) and efeito_elemento:

            nome_efeito = efeito_elemento.get(
                "nome",
                "Efeito Elemental"
            )

            descricao_efeito = efeito_elemento.get(
                "descricao",
                ""
            )

            texto_elemento = (
                f"**{nome_efeito}**"
            )

            if descricao_efeito:

                texto_elemento += (
                    f"\n{descricao_efeito}"
                )

            embed.add_field(
                name="🌈 Efeito Elemental",
                value=texto_elemento,
                inline=False
            )

        embed.set_footer(
            text=(
                f"Use: !usarmagia "
                f"<forma> <elemento>"
            )
        )

        await ctx.send(embed=embed)


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(
        Magias(bot)
    )