import discord
import datetime

from discord.ext import commands

from database.python.Mora import (
    obter_mora,
    adicionar_mora,
    remover_mora,
    depositar_mora,
    sacar_mora,
    pagar_mora,
    ranking_mora,
    economia_mora
)
fuso = datetime.timezone(datetime.timedelta(hours = -3))
horario = datetime.datetime.now(fuso)

class Mora(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    # ==========================================
    # SALDO
    # ==========================================

    @commands.command(name='msaldo')
    async def msaldo(self, ctx):

        jogador = obter_mora(
            ctx.author.id,
            ctx.guild.id
        )

        carteira = jogador["carteira"]
        banco = jogador["banco"]
        total = carteira + banco

        MSG = discord.Embed(
            title=f"| Saldo de {ctx.author.display_name}",
            color=discord.Color.green(),
            timestamp=horario
        )

        MSG.add_field(
            name="💰 Carteira",
            value=f"**{carteira:,} Mora**",
            inline=True
        )

        MSG.add_field(
            name="🏦 Banco",
            value=f"**{banco:,} Mora**",
            inline=True
        )

        MSG.add_field(
            name="💎 Total",
            value=f"**{total:,} Mora**",
            inline=False
        )

        MSG.set_footer(
            text="Tensura Moon - Korczak Technologies!"
        )

        await ctx.send(embed=MSG)


    # ==========================================
    # PAGAR
    # ==========================================

    @commands.command(name='mpagar')
    async def mpagar(self, ctx, quantidade: int):

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
                description="**Você não pode transferir Mora para si mesmo!**",
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
                description="**Você não pode transferir Mora para um bot!**",
                color=0xff0000,
                timestamp=horario
            )

            ERRO.set_footer(
                text="Tensura Moon - Korczak Technologies!"
            )

            await ctx.send(embed=ERRO)
            return

        try:

            pagar_mora(
                ctx.author.id,
                destinatario.id,
                ctx.guild.id,
                quantidade
            )

        except ValueError:

            ERRO = discord.Embed(
                title="| Erro",
                description="**Você não possui Mora suficiente!**",
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
                f"Você transferiu **{quantidade:,} Mora** "
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

    @commands.command(name='mdepositar')
    async def depositar(self, ctx, quantidade: int):

        if quantidade <= 0:

            await ctx.send(
                "A quantidade deve ser maior que 0."
            )

            return

        try:

            saldo = depositar_mora(
                ctx.author.id,
                ctx.guild.id,
                quantidade
            )

        except ValueError:

            ERRO = discord.Embed(
                title="| Erro",
                description="**Você não possui Mora suficiente na carteira!**",
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
                f"Você depositou **{quantidade:,} Mora**.\n\n"
                f"💰 Carteira: **{saldo['carteira']:,} Mora**\n"
                f"🏦 Banco: **{saldo['banco']:,} Mora**"
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

    @commands.command(name='msacar')
    async def sacar(self, ctx, quantidade: int):

        if quantidade <= 0:

            await ctx.send(
                "A quantidade deve ser maior que 0."
            )

            return

        try:

            saldo = sacar_mora(
                ctx.author.id,
                ctx.guild.id,
                quantidade
            )

        except ValueError:

            ERRO = discord.Embed(
                title="| Erro",
                description="**Você não possui essa quantidade de Mora no banco!**",
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
                f"Você sacou **{quantidade:,} Mora**.\n\n"
                f"💰 Carteira: **{saldo['carteira']:,} Mora**\n"
                f"🏦 Banco: **{saldo['banco']:,} Mora**"
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

    @commands.command(name='mranking')
    async def ranking(self, ctx):

        jogadores = ranking_mora(
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
                f"💰 **{total:,} Mora**\n"
            )

        MSG = discord.Embed(
            title="| Ranking de Mora",
            description=descricao,
            color=discord.Color.gold(),
            timestamp=horario
        )

        MSG.set_footer(
            text="Tensura Moon - Korczak Technologies!"
        )

        await ctx.send(embed=MSG)


    # ==========================================
    # ADICIONAR MORA
    # ==========================================

    @commands.command(name='madicionar-mora')
    @commands.has_permissions(administrator=True)
    async def adicionar_mora_cmd(
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

            saldo = adicionar_mora(
                jogador.id,
                ctx.guild.id,
                quantidade
            )

        except ValueError as erro:

            await ctx.send(str(erro))
            return

        MSG = discord.Embed(
            title="| Mora adicionada",
            description=(
                f"{jogador.mention} recebeu "
                f"**{quantidade:,} Mora**.\n\n"
                f"Carteira: **{saldo:,} Mora**."
            ),
            color=discord.Color.green(),
            timestamp=horario
        )

        MSG.set_footer(
            text="Tensura Moon - Korczak Technologies!"
        )

        await ctx.send(embed=MSG)


    # ==========================================
    # REMOVER MORA
    # ==========================================

    @commands.command(name='mremover-mora')
    @commands.has_permissions(administrator=True)
    async def remover_mora_cmd(
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

            saldo = remover_mora(
                jogador.id,
                ctx.guild.id,
                quantidade
            )

        except ValueError as erro:

            await ctx.send(str(erro))
            return

        MSG = discord.Embed(
            title="| Mora removida",
            description=(
                f"Foram removidas **{quantidade:,} Mora** "
                f"de {jogador.mention}.\n\n"
                f"Carteira: **{saldo:,} Mora**."
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

    @commands.command(name='meconomia')
    async def economia(self, ctx):

        dados = economia_mora(
            ctx.guild.id
        )

        MSG = discord.Embed(
            title="| Economia do Servidor",
            color=discord.Color.blue(),
            timestamp=horario
        )

        MSG.add_field(
            name="💰 Mora em carteiras",
            value=f"**{dados['carteira_total']:,}**",
            inline=True
        )

        MSG.add_field(
            name="🏦 Mora nos bancos",
            value=f"**{dados['banco_total']:,}**",
            inline=True
        )

        MSG.add_field(
            name="💎 Mora total",
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
    await bot.add_cog(Mora(bot))