import discord
import random
import asyncio

from discord.ext import commands

from database.python.mongodb import db
from database.python.luta import (
    MONSTROS,
    pode_lutar,
    criar_participante_jogador,
    criar_monstro,
    calcular_dano,
    finalizar_combate,
    obter_vencedores
)


class Luta(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # Combates ativos por canal
        self.combates = {}

        # Desafios PvP pendentes
        self.desafios = {}


    # ==========================================
    # COMANDO PRINCIPAL
    # ==========================================

    @commands.group(
        name="luta",
        aliases=["fight"],
        invoke_without_command=True
    )
    async def luta(self, ctx):

        embed = discord.Embed(
            title="⚔️ Sistema de Luta",
            color=discord.Color.red()
        )

        embed.add_field(
            name="📋 PvE",
            value=(
                "`!luta pve <monstro>` - Lutar contra monstro\n"
                "`!luta monstros` - Ver monstros"
            ),
            inline=False
        )

        embed.add_field(
            name="⚔️ PvP",
            value=(
                "`!luta pvp @jogador` - Desafiar jogador\n"
                "`!luta aceitar` - Aceitar desafio\n"
                "`!luta recusar` - Recusar desafio"
            ),
            inline=False
        )

        embed.add_field(
            name="🥊 Combate",
            value=(
                "`!soco` - Atacar\n"
                "`!chute` - Atacar\n"
                "`!defesa` - Defender\n"
                "`!esquiva` - Tentar esquivar\n"
                "`!fugir` - Fugir do PvE\n"
                "`!rluta` - Resetar combate"
            ),
            inline=False
        )

        embed.add_field(
            name="🔄 Sistema de Turnos",
            value=(
                "**1.** Um participante ataca\n"
                "**2.** O defensor escolhe Defesa ou Esquiva\n"
                "**3.** O ataque é resolvido\n"
                "**4.** O defensor se torna o próximo atacante"
            ),
            inline=False
        )

        await ctx.send(embed=embed)


    # ==========================================
    # LISTAR MONSTROS
    # ==========================================

    @luta.command(name="monstros")
    async def luta_monstros(self, ctx):

        if not MONSTROS:
            await ctx.send(
                "❌ Nenhum monstro foi carregado."
            )
            return

        embed = discord.Embed(
            title="🐉 Monstros",
            color=discord.Color.dark_red()
        )

        for id_monstro, dados in list(MONSTROS.items())[:10]:

            embed.add_field(
                name=(
                    f"{dados.get('emoji', '👹')} "
                    f"{dados.get('nome', id_monstro)}"
                ),
                value=(
                    f"**Vida:** {dados.get('vida_base', 0)}\n"
                    f"**Dano:** {dados.get('dano_base', 0)}\n"
                    f"**XP:** {dados.get('xp_recompensa', 0)}\n"
                    f"**Hunos:** {dados.get('hunos_recompensa', 0)}"
                ),
                inline=True
            )

        await ctx.send(embed=embed)


    # ==========================================
    # INICIAR PVE
    # ==========================================

    @luta.command(name="pve")
    async def luta_pve(
        self,
        ctx,
        monstro_tipo: str
    ):

        if ctx.channel.id in self.combates:

            combate = self.combates[ctx.channel.id]

            if combate.get("ativo", False):
                await ctx.send(
                    "❌ Já existe uma batalha ativa neste canal."
                )
                return

        if monstro_tipo not in MONSTROS:
            await ctx.send(
                f"❌ Monstro `{monstro_tipo}` não encontrado."
            )
            return

        verificacao = pode_lutar(
            str(ctx.author.id),
            str(ctx.guild.id)
        )

        if not verificacao.get("pode", False):
            await ctx.send(
                verificacao.get(
                    "mensagem",
                    "❌ Você não pode lutar."
                )
            )
            return

        jogador = criar_participante_jogador(
            str(ctx.author.id),
            str(ctx.guild.id)
        )

        if not jogador:
            await ctx.send(
                "❌ Você não está registrado."
            )
            return

        jogador["nome"] = (
            jogador.get("nome")
            or ctx.author.display_name
        )

        monstro = criar_monstro(
            monstro_tipo,
            1
        )

        if not monstro:
            await ctx.send(
                "❌ Não foi possível criar esse monstro."
            )
            return

        participantes = [
            jogador,
            monstro
        ]

        participantes.sort(
            key=lambda participante:
                participante.get("velocidade", 0),
            reverse=True
        )

        atacante = participantes[0]
        defensor = participantes[1]

        self.combates[ctx.channel.id] = {
            "participantes": participantes,
            "turno": 0,
            "numero_turno": 1,
            "fase": "ataque",
            "ativo": True,
            "guild_id": str(ctx.guild.id),
            "pvp": False,
            "historico": [],
            "ataque_pendente": None
        }

        db["Jogadores"].update_one(
            {
                "ID": str(ctx.author.id),
                "guild_id": str(ctx.guild.id)
            },
            {
                "$set": {
                    "Situação": "ativo_combate"
                }
            }
        )

        await self._mostrar_inicio(
            ctx,
            atacante,
            defensor,
            participantes,
            "PvE"
        )


    # ==========================================
    # DESAFIAR JOGADOR - PVP
    # ==========================================

    @luta.command(name="pvp")
    async def luta_pvp(
        self,
        ctx,
        jogador_desafiado: discord.Member
    ):

        # Não desafiar a si mesmo
        if jogador_desafiado.id == ctx.author.id:
            await ctx.send(
                "❌ Você não pode desafiar a si mesmo."
            )
            return

        # Não desafiar bot
        if jogador_desafiado.bot:
            await ctx.send(
                "❌ Você não pode desafiar um bot."
            )
            return

        # Verifica combate ativo no canal
        if ctx.channel.id in self.combates:

            combate = self.combates[ctx.channel.id]

            if combate.get("ativo", False):
                await ctx.send(
                    "❌ Já existe um combate ativo neste canal."
                )
                return

        # Verifica desafiante
        verificacao_desafiante = pode_lutar(
            str(ctx.author.id),
            str(ctx.guild.id)
        )

        if not verificacao_desafiante.get("pode", False):
            await ctx.send(
                verificacao_desafiante.get(
                    "mensagem",
                    "❌ Você não pode lutar."
                )
            )
            return

        # Verifica desafiado
        verificacao_desafiado = pode_lutar(
            str(jogador_desafiado.id),
            str(ctx.guild.id)
        )

        if not verificacao_desafiado.get("pode", False):
            await ctx.send(
                f"❌ {jogador_desafiado.mention} não pode lutar."
            )
            return

        # Cria desafio
        self.desafios[ctx.channel.id] = {
            "desafiante_id": str(ctx.author.id),
            "desafiado_id": str(jogador_desafiado.id),
            "guild_id": str(ctx.guild.id)
        }

        embed = discord.Embed(
            title="⚔️ Desafio PvP!",
            description=(
                f"{ctx.author.mention} desafiou "
                f"{jogador_desafiado.mention} para uma luta!"
            ),
            color=discord.Color.orange()
        )

        embed.add_field(
            name="📋 Resposta",
            value=(
                f"{jogador_desafiado.mention}, use:\n"
                "`!luta aceitar`\n"
                "ou\n"
                "`!luta recusar`"
            ),
            inline=False
        )

        await ctx.send(embed=embed)


    # ==========================================
    # ACEITAR DESAFIO PVP
    # ==========================================

    @luta.command(name="aceitar")
    async def luta_aceitar(self, ctx):

        desafio = self.desafios.get(
            ctx.channel.id
        )

        if not desafio:
            await ctx.send(
                "❌ Não existe nenhum desafio PvP pendente."
            )
            return

        if desafio["desafiado_id"] != str(ctx.author.id):
            await ctx.send(
                "❌ Esse desafio não é para você."
            )
            return

        if ctx.channel.id in self.combates:

            combate = self.combates[ctx.channel.id]

            if combate.get("ativo", False):
                await ctx.send(
                    "❌ Já existe um combate ativo neste canal."
                )
                return

        desafiante_id = desafio["desafiante_id"]
        desafiado_id = desafio["desafiado_id"]
        guild_id = desafio["guild_id"]

        # Verifica novamente os jogadores
        verificacao_1 = pode_lutar(
            desafiante_id,
            guild_id
        )

        verificacao_2 = pode_lutar(
            desafiado_id,
            guild_id
        )

        if not verificacao_1.get("pode", False):
            await ctx.send(
                "❌ O desafiante não pode mais lutar."
            )
            del self.desafios[ctx.channel.id]
            return

        if not verificacao_2.get("pode", False):
            await ctx.send(
                "❌ Você não pode mais lutar."
            )
            del self.desafios[ctx.channel.id]
            return

        jogador_1 = criar_participante_jogador(
            desafiante_id,
            guild_id
        )

        jogador_2 = criar_participante_jogador(
            desafiado_id,
            guild_id
        )

        if not jogador_1 or not jogador_2:
            await ctx.send(
                "❌ Não foi possível carregar os jogadores."
            )
            del self.desafios[ctx.channel.id]
            return

        # Obtém os nomes atuais
        membro_1 = ctx.guild.get_member(
            int(desafiante_id)
        )

        membro_2 = ctx.guild.get_member(
            int(desafiado_id)
        )

        if membro_1:
            jogador_1["nome"] = membro_1.display_name

        if membro_2:
            jogador_2["nome"] = membro_2.display_name

        participantes = [
            jogador_1,
            jogador_2
        ]

        # Quem tem maior velocidade começa
        participantes.sort(
            key=lambda participante:
                participante.get("velocidade", 0),
            reverse=True
        )

        atacante = participantes[0]
        defensor = participantes[1]

        # Se velocidades forem iguais,
        # sorteia o primeiro atacante
        if (
            participantes[0].get("velocidade", 0)
            == participantes[1].get("velocidade", 0)
        ):
            random.shuffle(participantes)

            atacante = participantes[0]
            defensor = participantes[1]

        self.combates[ctx.channel.id] = {
            "participantes": participantes,
            "turno": 0,
            "numero_turno": 1,
            "fase": "ataque",
            "ativo": True,
            "guild_id": guild_id,
            "pvp": True,
            "historico": [],
            "ataque_pendente": None
        }

        # Coloca os dois em combate
        for participante in participantes:

            db["Jogadores"].update_one(
                {
                    "ID": participante["id"],
                    "guild_id": guild_id
                },
                {
                    "$set": {
                        "Situação": "ativo_combate"
                    }
                }
            )

        # Remove desafio
        del self.desafios[ctx.channel.id]

        await self._mostrar_inicio(
            ctx,
            atacante,
            defensor,
            participantes,
            "PvP"
        )


    # ==========================================
    # RECUSAR DESAFIO PVP
    # ==========================================

    @luta.command(name="recusar")
    async def luta_recusar(self, ctx):

        desafio = self.desafios.get(
            ctx.channel.id
        )

        if not desafio:
            await ctx.send(
                "❌ Não existe nenhum desafio pendente."
            )
            return

        if desafio["desafiado_id"] != str(ctx.author.id):
            await ctx.send(
                "❌ Você não pode recusar esse desafio."
            )
            return

        del self.desafios[ctx.channel.id]

        await ctx.send(
            f"❌ {ctx.author.mention} recusou o desafio."
        )


    # ==========================================
    # MOSTRAR INÍCIO
    # ==========================================

    async def _mostrar_inicio(
        self,
        ctx,
        atacante,
        defensor,
        participantes,
        modo
    ):

        embed = discord.Embed(
            title=f"⚔️ Combate {modo} iniciado!",
            description=(
                f"🔔 **Turno 1**\n\n"
                f"⚔️ **{atacante['nome']}** "
                "começa atacando!"
            ),
            color=discord.Color.red()
        )

        embed.add_field(
            name="🎯 Defensor",
            value=(
                f"🛡️ **{defensor['nome']}**"
            ),
            inline=False
        )

        embed.add_field(
            name="📋 Status",
            value=self._texto_status(participantes),
            inline=False
        )

        if atacante["tipo"] == "jogador":

            embed.set_footer(
                text="Use !soco ou !chute para atacar."
            )

            await ctx.send(embed=embed)

        else:

            embed.set_footer(
                text="O monstro está preparando seu ataque..."
            )

            await ctx.send(embed=embed)

            await asyncio.sleep(1)

            await self._ataque_monstro(ctx)


    # ==========================================
    # TEXTO DE STATUS
    # ==========================================

    def _texto_status(self, participantes):

        texto = ""

        for participante in participantes:

            if participante["tipo"] == "jogador":

                texto += (
                    f"👤 **{participante['nome']}**\n"
                    f"❤️ {participante['vida']}"
                    f"/{participante['vida_maxima']}\n"
                    f"💙 {participante.get('mana', 0)}\n\n"
                )

            else:

                texto += (
                    f"{participante.get('emoji', '👹')} "
                    f"**{participante['nome']}**\n"
                    f"❤️ {participante['vida']}"
                    f"/{participante['vida_maxima']}\n\n"
                )

        return texto


    # ==========================================
    # OBTER COMBATE
    # ==========================================

    def _obter_combate(self, channel_id):

        return self.combates.get(channel_id)


    # ==========================================
    # OBTER ATACANTE
    # ==========================================

    def _obter_atacante(self, combate):

        return combate["participantes"][
            combate["turno"]
        ]


    # ==========================================
    # OBTER DEFENSOR
    # ==========================================

    def _obter_defensor(self, combate):

        participantes = combate["participantes"]

        indice = (
            combate["turno"] + 1
        ) % len(participantes)

        return participantes[indice]


    # ==========================================
    # ATAQUE DO JOGADOR
    # ==========================================

    async def _ataque_jogador(
        self,
        ctx,
        tipo_ataque
    ):

        combate = self._obter_combate(
            ctx.channel.id
        )

        if not combate:

            await ctx.send(
                "❌ Não há batalha ativa."
            )
            return

        if not combate.get("ativo", False):
            await ctx.send(
                "❌ Esta batalha terminou."
            )
            return

        if combate["fase"] != "ataque":
            await ctx.send(
                "❌ O ataque anterior ainda precisa ser defendido."
            )
            return

        atacante = self._obter_atacante(combate)
        defensor = self._obter_defensor(combate)

        if atacante["tipo"] != "jogador":

            await ctx.send(
                f"⏳ É a vez de **{atacante['nome']}**."
            )
            return

        if atacante["id"] != str(ctx.author.id):

            await ctx.send(
                f"❌ Não é sua vez. "
                f"Agora é a vez de **{atacante['nome']}**."
            )
            return

        if tipo_ataque == "soco":
            nome_ataque = "👊 Soco"

        elif tipo_ataque == "chute":
            nome_ataque = "🦵 Chute"

        else:
            nome_ataque = "⚔️ Ataque"

        combate["ataque_pendente"] = {
            "atacante_id": atacante["id"],
            "defensor_id": defensor["id"],
            "tipo": tipo_ataque,
            "nome": nome_ataque
        }

        # Agora o defensor deve agir
        combate["fase"] = "defesa"

        mensagem = (
            f"{nome_ataque}\n\n"
            f"⚔️ **{atacante['nome']}** "
            f"atacou **{defensor['nome']}**!\n\n"
            f"🛡️ Agora **{defensor['nome']}** "
            "deve se defender."
        )

        embed = discord.Embed(
            title=f"⚔️ Turno {combate['numero_turno']}",
            description=mensagem,
            color=discord.Color.orange()
        )

        embed.add_field(
            name="📋 Status",
            value=self._texto_status(
                combate["participantes"]
            ),
            inline=False
        )

        # Monstro se defende automaticamente
        if defensor["tipo"] == "monstro":

            embed.set_footer(
                text="O monstro está reagindo..."
            )

            await ctx.send(embed=embed)

            await asyncio.sleep(1)

            await self._defesa_monstro(ctx)

            return

        # Jogador precisa escolher
        embed.set_footer(
            text=(
                f"{defensor['nome']}: "
                "use !defesa ou !esquiva."
            )
        )

        await ctx.send(embed=embed)


    # ==========================================
    # COMANDO SOCO
    # ==========================================

    @commands.command(name="soco")
    async def soco(self, ctx):

        await self._ataque_jogador(
            ctx,
            "soco"
        )


    # ==========================================
    # COMANDO CHUTE
    # ==========================================

    @commands.command(name="chute")
    async def chute(self, ctx):

        await self._ataque_jogador(
            ctx,
            "chute"
        )


    # ==========================================
    # ATAQUE DO MONSTRO
    # ==========================================

    async def _ataque_monstro(self, ctx):

        combate = self._obter_combate(
            ctx.channel.id
        )

        if not combate:
            return

        if not combate.get("ativo", False):
            return

        if combate["fase"] != "ataque":
            return

        atacante = self._obter_atacante(combate)
        defensor = self._obter_defensor(combate)

        if atacante["tipo"] != "monstro":
            return

        combate["ataque_pendente"] = {
            "atacante_id": atacante["id"],
            "defensor_id": defensor["id"],
            "tipo": "ataque_monstro",
            "nome": "⚔️ Ataque do Monstro"
        }

        combate["fase"] = "defesa"

        embed = discord.Embed(
            title=f"⚔️ Turno {combate['numero_turno']}",
            description=(
                f"{atacante.get('emoji', '👹')} "
                f"**{atacante['nome']}** "
                f"atacou **{defensor['nome']}**!\n\n"
                f"🛡️ **{defensor['nome']}**, "
                "escolha sua defesa!"
            ),
            color=discord.Color.dark_red()
        )

        embed.add_field(
            name="📋 Status",
            value=self._texto_status(
                combate["participantes"]
            ),
            inline=False
        )

        embed.set_footer(
            text="Use !defesa ou !esquiva."
        )

        await ctx.send(embed=embed)


    # ==========================================
    # DEFESA DO JOGADOR
    # ==========================================

    async def _defesa_jogador(
        self,
        ctx,
        acao
    ):

        combate = self._obter_combate(
            ctx.channel.id
        )

        if not combate:

            await ctx.send(
                "❌ Não há batalha ativa."
            )
            return

        if not combate.get("ativo", False):
            return

        if combate["fase"] != "defesa":

            await ctx.send(
                "❌ Não existe nenhum ataque para defender."
            )
            return

        atacante = self._obter_atacante(combate)
        defensor = self._obter_defensor(combate)

        if defensor["tipo"] != "jogador":

            await ctx.send(
                "❌ Agora não é um jogador que deve defender."
            )
            return

        if defensor["id"] != str(ctx.author.id):

            await ctx.send(
                f"❌ É **{defensor['nome']}** "
                "quem deve defender."
            )
            return

        if acao == "defesa":

            defensor["defesa_ativa"] = True
            defensor["esquiva_ativa"] = False

            mensagem = (
                f"🛡️ **{defensor['nome']}** "
                "preparou sua defesa!"
            )

            cor = discord.Color.blue()

        else:

            defensor["esquiva_ativa"] = True
            defensor["defesa_ativa"] = False

            mensagem = (
                f"💨 **{defensor['nome']}** "
                "tentou esquivar!"
            )

            cor = discord.Color.blue()

        await ctx.send(
            embed=discord.Embed(
                title="🛡️ Defesa",
                description=mensagem,
                color=cor
            )
        )

        await asyncio.sleep(0.5)

        await self._resolver_ataque(ctx)


    # ==========================================
    # COMANDO DEFESA
    # ==========================================

    @commands.command(name="defesa")
    async def defesa(self, ctx):

        await self._defesa_jogador(
            ctx,
            "defesa"
        )


    # ==========================================
    # COMANDO ESQUIVA
    # ==========================================

    @commands.command(name="esquiva")
    async def esquiva(self, ctx):

        await self._defesa_jogador(
            ctx,
            "esquiva"
        )


    # ==========================================
    # DEFESA DO MONSTRO
    # ==========================================

    async def _defesa_monstro(self, ctx):

        combate = self._obter_combate(
            ctx.channel.id
        )

        if not combate:
            return

        if combate["fase"] != "defesa":
            return

        defensor = self._obter_defensor(combate)

        if defensor["tipo"] != "monstro":
            return

        escolha = random.choice([
            "defesa",
            "esquiva",
            "normal"
        ])

        if escolha == "defesa":

            defensor["defesa_ativa"] = True
            defensor["esquiva_ativa"] = False

            mensagem = (
                f"🛡️ **{defensor['nome']}** "
                "preparou sua defesa!"
            )

        elif escolha == "esquiva":

            defensor["esquiva_ativa"] = True
            defensor["defesa_ativa"] = False

            mensagem = (
                f"💨 **{defensor['nome']}** "
                "tentou esquivar!"
            )

        else:

            defensor["defesa_ativa"] = False
            defensor["esquiva_ativa"] = False

            mensagem = (
                f"😨 **{defensor['nome']}** "
                "não conseguiu se defender!"
            )

        await ctx.send(
            embed=discord.Embed(
                title="🛡️ Defesa do Monstro",
                description=mensagem,
                color=discord.Color.dark_gold()
            )
        )

        await asyncio.sleep(0.5)

        await self._resolver_ataque(ctx)


    # ==========================================
    # RESOLVER ATAQUE
    # ==========================================

    async def _resolver_ataque(self, ctx):

        combate = self._obter_combate(
            ctx.channel.id
        )

        if not combate:
            return

        atacante = self._obter_atacante(combate)
        defensor = self._obter_defensor(combate)

        dano, resultado = calcular_dano(
            atacante,
            defensor
        )

        if resultado == "esquivou":

            mensagem = (
                f"💨 **{defensor['nome']}** "
                f"esquivou completamente do ataque de "
                f"**{atacante['nome']}**!"
            )

        else:

            defensor["vida"] = max(
                0,
                defensor["vida"] - dano
            )

            mensagem = (
                f"⚔️ **{atacante['nome']}** "
                f"causou **{dano} de dano** em "
                f"**{defensor['nome']}**!"
            )

            if defensor["vida"] <= 0:

                mensagem += (
                    f"\n\n💀 **{defensor['nome']} "
                    "foi derrotado!**"
                )

        # Estados defensivos são consumidos
        defensor["defesa_ativa"] = False
        defensor["esquiva_ativa"] = False

        embed = discord.Embed(
            title="💥 Resultado do Ataque",
            description=mensagem,
            color=discord.Color.red()
        )

        embed.add_field(
            name="📋 Status Atual",
            value=self._texto_status(
                combate["participantes"]
            ),
            inline=False
        )

        await ctx.send(embed=embed)

        resultado_combate = obter_vencedores(
            combate
        )

        if resultado_combate:

            combate["ativo"] = False

            await self._finalizar(ctx)

            return

        await asyncio.sleep(1)

        await self._proximo_turno(ctx)


    # ==========================================
    # PRÓXIMO TURNO
    # ==========================================

    async def _proximo_turno(self, ctx):

        combate = self._obter_combate(
            ctx.channel.id
        )

        if not combate:
            return

        if not combate.get("ativo", False):
            return

        participantes = combate["participantes"]

        # O antigo defensor vira atacante
        combate["turno"] = (
            combate["turno"] + 1
        ) % len(participantes)

        combate["numero_turno"] += 1

        combate["fase"] = "ataque"

        combate["ataque_pendente"] = None

        atacante = self._obter_atacante(combate)
        defensor = self._obter_defensor(combate)

        embed = discord.Embed(
            title=f"🔄 Turno {combate['numero_turno']}",
            description=(
                f"⚔️ Agora é a vez de "
                f"**{atacante['nome']}** atacar!"
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="🎯 Defensor",
            value=f"🛡️ **{defensor['nome']}**",
            inline=False
        )

        if atacante["tipo"] == "jogador":

            embed.set_footer(
                text="Use !soco ou !chute."
            )

            await ctx.send(embed=embed)

        else:

            embed.set_footer(
                text="O monstro está preparando seu ataque..."
            )

            await ctx.send(embed=embed)

            await asyncio.sleep(1)

            await self._ataque_monstro(ctx)


    # ==========================================
    # FUGIR
    # ==========================================

    @commands.command(name="fugir")
    async def fugir(self, ctx):

        combate = self._obter_combate(
            ctx.channel.id
        )

        if not combate:

            await ctx.send(
                "❌ Você não está em combate."
            )
            return

        # PvP não permite fugir
        if combate.get("pvp", False):

            await ctx.send(
                "❌ Não é possível fugir de um combate PvP."
            )
            return

        jogador = None

        for participante in combate["participantes"]:

            if (
                participante["tipo"] == "jogador"
                and participante["id"] == str(ctx.author.id)
            ):
                jogador = participante
                break

        if not jogador:

            await ctx.send(
                "❌ Você não participa deste combate."
            )
            return

        chance_fuga = 0.15

        if random.random() < chance_fuga:

            combate["ativo"] = False

            db["Jogadores"].update_one(
                {
                    "ID": jogador["id"],
                    "guild_id": combate["guild_id"]
                },
                {
                    "$set": {
                        "Situação": "ativo",
                        "Vida": jogador["vida"],
                        "Mana": jogador.get("mana", 0)
                    }
                }
            )

            await ctx.send(
                f"💨 **{jogador['nome']}** conseguiu fugir!"
            )

            if ctx.channel.id in self.combates:
                del self.combates[ctx.channel.id]

        else:

            await ctx.send(
                "❌ Você não conseguiu fugir!"
            )


    # ==========================================
    # FINALIZAR COMBATE
    # ==========================================

    async def _finalizar(self, ctx):

        combate = self._obter_combate(
            ctx.channel.id
        )

        if not combate:
            return

        combate["ativo"] = False

        resultado = obter_vencedores(
            combate
        )

        recompensas = finalizar_combate(
            combate
        )

        if resultado == "jogadores":

            descricao = (
                "🏆 Os jogadores venceram o combate!"
            )

            cor = discord.Color.green()

        elif resultado == "monstros":

            descricao = (
                "💀 Os monstros venceram o combate!"
            )

            cor = discord.Color.red()

        else:

            descricao = (
                "⚠️ O combate terminou sem vencedores."
            )

            cor = discord.Color.greyple()

        embed = discord.Embed(
            title="⚔️ Combate Finalizado",
            description=descricao,
            color=cor
        )

        # Recompensas apenas quando existirem
        if recompensas:

            xp = recompensas.get("xp", 0)
            hunos = recompensas.get("hunos", 0)

            if xp > 0 or hunos > 0:

                embed.add_field(
                    name="🎁 Recompensas",
                    value=(
                        f"✨ XP: **{xp}**\n"
                        f"💰 Hunos: **{hunos}**"
                    ),
                    inline=False
                )

        embed.add_field(
            name="📋 Status Final",
            value=self._texto_status(
                combate["participantes"]
            ),
            inline=False
        )

        await ctx.send(embed=embed)

        if ctx.channel.id in self.combates:
            del self.combates[ctx.channel.id]


    # ==========================================
    # RESETAR LUTA
    # ==========================================

    @commands.command(
        name="rluta",
        aliases=["resetarluta"]
    )
    async def rluta(self, ctx):

        combate = self._obter_combate(
            ctx.channel.id
        )

        if not combate:

            await ctx.send(
                "❌ Não existe combate ativo neste canal."
            )
            return

        for participante in combate["participantes"]:

            if participante["tipo"] != "jogador":
                continue

            db["Jogadores"].update_one(
                {
                    "ID": participante["id"],
                    "guild_id": combate["guild_id"]
                },
                {
                    "$set": {
                        "Situação": "ativo",
                        "Vida": participante["vida"],
                        "Mana": participante.get(
                            "mana",
                            0
                        )
                    }
                }
            )

        del self.combates[ctx.channel.id]

        await ctx.send(
            "🔄 Combate resetado com sucesso."
        )


# ==========================================
# SETUP
# ==========================================

async def setup(bot):

    await bot.add_cog(
        Luta(bot)
    )