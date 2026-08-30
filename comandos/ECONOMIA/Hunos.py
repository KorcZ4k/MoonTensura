import discord
import datetime
from discord.ext import commands

from database.python.Hunos import (
    obter_hunos,
    adicionar_hunos,
    remover_hunos,
    depositar_hunos,
    sacar_hunos,
    pagar_hunos,
    ranking_hunos,
    economia_hunos
)
fuso = datetime.timezone(datetime.timedelta(hours = -3))
horario = datetime.datetime.now(fuso)

class Hunos(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    # ==========================================
    # SALDO
    # ==========================================

    @commands.command(name='saldo')
    async def saldo(self, ctx):

        jogador = obter_hunos(
            ctx.author.id,
            ctx.guild.id
        )

        carteira = jogador["carteira"]
        banco = jogador["banco"]
        total = carteira + banco

        MSG = discord.Embed(
            title=f"| Saldo de {ctx.author.display_name}",
            description="Saldo de Hunos",
            color=discord.Color.green(),
            timestamp=horario
        )

        MSG.add_field(
            name="💰 Carteira",
            value=f"**{carteira:,} Hunos**",
            inline=True
        )

        MSG.add_field(
            name="🏦 Banco",
            value=f"**{banco:,} Hunos**",
            inline=True
        )

        MSG.add_field(
            name="💎 Total",
            value=f"**{total:,} Hunos**",
            inline=False
        )

        MSG.set_footer(
            text="Tensura Moon - Korczak Technologies!"
        )

        await ctx.send(embed=MSG)


    # ==========================================
    # PAGAR
    # ==========================================

    @commands.command(name='pagar')
    async def pagar(self, ctx, quantidade: int):

        mencoes = ctx.message.mentions

        if len(mencoes) != 1:

            ERRO = discord.Embed(
                title="| Erro",
                description="**Você precisa mencionar exatamente um usuário!**",
                color=0xff0000,
                timestamp=horario
            )

            ERRO.set_footer(
                text="Tensura Moon - Korczak Technologies!"
            )

            await ctx.send(embed=ERRO)
            return

        destinatario = mencoes[0]

        if quantidade <= 0:

            ERRO = discord.Embed(
                title="| Erro",
                description="**A quantidade deve ser maior que 0!**",
                color=0xff0000,
                timestamp=horario
            )

            ERRO.set_footer(
                text="Tensura Moon - Korczak Technologies!"
            )

            await ctx.send(embed=ERRO)
            return

        if destinatario.id == ctx.author.id:

            ERRO = discord.Embed(
                title="| Erro",
                description="**Você não pode transferir Hunos para si mesmo!**",
                color=0xff0000,
                timestamp=horario
            )

            ERRO.set_footer(
                text="Tensura Moon - Korczak Technologies!"
            )

            await ctx.send(embed=ERRO)
            return

        if destinatario.bot:

            ERRO = discord.Embed(
                title="| Erro",
                description="**Você não pode transferir Hunos para um bot!**",
                color=0xff0000,
                timestamp=horario
            )

            ERRO.set_footer(
                text="Tensura Moon - Korczak Technologies!"
            )

            await ctx.send(embed=ERRO)
            return

        try:

            pagar_hunos(
                ctx.author.id,
                destinatario.id,
                ctx.guild.id,
                quantidade
            )

        except ValueError:

            ERRO = discord.Embed(
                title="| Erro",
                description="**Você não possui Hunos suficientes!**",
                color=0xff0000,
                timestamp=horario
            )

            ERRO.set_footer(
                text="Tensura Moon - Korczak Technologies!"
            )

            await ctx.send(embed=ERRO)
            return

        MSG = discord.Embed(
            title="| Transferência",
            description=(
                f"Você transferiu **{quantidade:,} Hunos** "
                f"para {destinatario.mention}!"
            ),
            color=discord.Color.green(),
            timestamp=horario
        )

        MSG.set_footer(
            text="Tensura Moon - Korczak Technologies!"
        )

        await ctx.send(embed=MSG)


    # ==========================================
    # DEPOSITAR
    # ==========================================

    @commands.command(name='depositar')
    async def depositar(self, ctx, quantidade: int):

        if quantidade <= 0:

            await ctx.send(
                "A quantidade deve ser maior que 0."
            )

            return

        try:

            saldo = depositar_hunos(
                ctx.author.id,
                ctx.guild.id,
                quantidade
            )

        except ValueError:

            ERRO = discord.Embed(
                title="| Erro",
                description="**Você não possui Hunos suficientes na carteira!**",
                color=0xff0000,
                timestamp=horario
            )

            ERRO.set_footer(
                text="Tensura Moon - Korczak Technologies!"
            )

            await ctx.send(embed=ERRO)
            return

        MSG = discord.Embed(
            title="| Banco",
            description=(
                f"Você depositou **{quantidade:,} Hunos**.\n\n"
                f"💰 Carteira: **{saldo['carteira']:,} Hunos**\n"
                f"🏦 Banco: **{saldo['banco']:,} Hunos**"
            ),
            color=discord.Color.green(),
            timestamp=horario
        )

        MSG.set_footer(
            text="Tensura Moon - Korczak Technologies!"
        )

        await ctx.send(embed=MSG)


    # ==========================================
    # SACAR
    # ==========================================

    @commands.command(name='sacar')
    async def sacar(self, ctx, quantidade: int):

        if quantidade <= 0:

            await ctx.send(
                "A quantidade deve ser maior que 0."
            )

            return

        try:

            saldo = sacar_hunos(
                ctx.author.id,
                ctx.guild.id,
                quantidade
            )

        except ValueError:

            ERRO = discord.Embed(
                title="| Erro",
                description="**Você não possui essa quantidade de Hunos no banco!**",
                color=0xff0000,
                timestamp=horario
            )

            ERRO.set_footer(
                text="Tensura Moon - Korczak Technologies!"
            )

            await ctx.send(embed=ERRO)
            return

        MSG = discord.Embed(
            title="| Banco",
            description=(
                f"Você sacou **{quantidade:,} Hunos**.\n\n"
                f"💰 Carteira: **{saldo['carteira']:,} Hunos**\n"
                f"🏦 Banco: **{saldo['banco']:,} Hunos**"
            ),
            color=discord.Color.green(),
            timestamp=horario
        )

        MSG.set_footer(
            text="Tensura Moon - Korczak Technologies!"
        )

        await ctx.send(embed=MSG)


    # ==========================================
    # RANKING
    # ==========================================

    @commands.command(name='ranking')
    async def ranking(self, ctx):

        jogadores = ranking_hunos(
            ctx.guild.id,
            10
        )

        if not jogadores:

            await ctx.send(
                "Ainda não existem jogadores registrados."
            )

            return

        descricao = ""

        for posicao, jogador in enumerate(jogadores, 1):

            carteira = jogador.get(
                "carteira",
                0
            )

            banco = jogador.get(
                "banco",
                0
            )

            total = carteira + banco

            membro = ctx.guild.get_member(
                int(jogador["ID"])
            )

            if membro:
                nome = membro.display_name
            else:
                nome = f"Usuário {jogador['ID']}"

            descricao += (
                f"**{posicao}.** {nome} — "
                f"💰 **{total:,} Hunos**\n"
            )

        MSG = discord.Embed(
            title="| Ranking de Hunos",
            description=descricao,
            color=discord.Color.gold(),
            timestamp=horario
        )

        MSG.set_footer(
            text="Tensura Moon - Korczak Technologies!"
        )

        await ctx.send(embed=MSG)


    # ==========================================
    # ADICIONAR HUNOS
    # ==========================================

    @commands.command(name='adicionar-hunos')
    @commands.has_permissions(administrator=True)
    async def adicionar_hunos_cmd(
        self,
        ctx,
        jogador: discord.Member,
        quantidade: int
    ):

        if quantidade <= 0:

            await ctx.send(
                "A quantidade deve ser maior que 0."
            )

            return

        try:

            saldo = adicionar_hunos(
                jogador.id,
                ctx.guild.id,
                quantidade
            )

        except ValueError as erro:

            await ctx.send(str(erro))
            return

        MSG = discord.Embed(
            title="| Hunos adicionados",
            description=(
                f"{jogador.mention} recebeu "
                f"**{quantidade:,} Hunos**.\n\n"
                f"Carteira: **{saldo:,} Hunos**."
            ),
            color=discord.Color.green(),
            timestamp=horario
        )

        MSG.set_footer(
            text="Tensura Moon - Korczak Technologies!"
        )

        await ctx.send(embed=MSG)


    # ==========================================
    # REMOVER HUNOS
    # ==========================================

    @commands.command(name='remover-hunos')
    @commands.has_permissions(administrator=True)
    async def remover_hunos_cmd(
        self,
        ctx,
        jogador: discord.Member,
        quantidade: int
    ):

        if quantidade <= 0:

            await ctx.send(
                "A quantidade deve ser maior que 0."
            )

            return

        try:

            saldo = remover_hunos(
                jogador.id,
                ctx.guild.id,
                quantidade
            )

        except ValueError as erro:

            await ctx.send(str(erro))
            return

        MSG = discord.Embed(
            title="| Hunos removidos",
            description=(
                f"Foram removidos **{quantidade:,} Hunos** "
                f"de {jogador.mention}.\n\n"
                f"Carteira: **{saldo:,} Hunos**."
            ),
            color=discord.Color.red(),
            timestamp=horario
        )

        MSG.set_footer(
            text="Tensura Moon - Korczak Technologies!"
        )

        await ctx.send(embed=MSG)


    # ==========================================
    # ECONOMIA
    # ==========================================

    @commands.command(name='economia')
    async def economia(self, ctx):

        dados = economia_hunos(
            ctx.guild.id
        )

        MSG = discord.Embed(
            title="| Economia de Hunos",
            color=discord.Color.blue(),
            timestamp=horario
        )

        MSG.add_field(
            name="💰 Hunos em carteiras",
            value=f"**{dados['carteira_total']:,}**",
            inline=True
        )

        MSG.add_field(
            name="🏦 Hunos nos bancos",
            value=f"**{dados['banco_total']:,}**",
            inline=True
        )

        MSG.add_field(
            name="💎 Hunos totais",
            value=f"**{dados['total']:,}**",
            inline=True
        )

        MSG.add_field(
            name="👥 Jogadores",
            value=f"**{dados['jogadores']:,}**",
            inline=True
        )

        MSG.set_footer(
            text="Tensura Moon - Korczak Technologies!"
        )

        await ctx.send(embed=MSG)


async def setup(bot):
    await bot.add_cog(Hunos(bot))
