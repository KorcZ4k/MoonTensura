import discord
from discord.ext import commands


class Ajuda(commands.Cog):
    """Menu de ajuda visual do TensuraBot."""

    def __init__(self, bot):
        self.bot = bot

    def _categoria(self, cog):
        if not cog:
            return "📌 Outros"
        nome = cog.__class__.__module__.lower()
        if ".rpg" in nome:
            return "⚔️ RPG"
        if ".economia" in nome:
            return "💰 Economia"
        if ".administracao" in nome:
            return "🛡️ Administração"
        return "📌 Outros"

    @commands.command(name="help", aliases=["ajuda"])
    async def help_command(self, ctx, *, comando: str = None):
        prefixo = ctx.clean_prefix

        if comando:
            cmd = self.bot.get_command(comando.lower())
            if not cmd:
                embed = discord.Embed(
                    title="❌ Comando não encontrado",
                    description=f"Não encontrei nenhum comando chamado `{comando}`.",
                    color=discord.Color.red(),
                )
                embed.set_footer(text=f"Use {prefixo}help para ver todos os comandos.")
                await ctx.send(embed=embed)
                return

            aliases = ", ".join(f"`{prefixo}{alias}`" for alias in cmd.aliases) or "Nenhum"
            embed = discord.Embed(
                title=f"📖 {prefixo}{cmd.name}",
                description=cmd.help or "Sem descrição disponível.",
                color=discord.Color.blurple(),
            )
            embed.add_field(name="Como usar", value=f"`{prefixo}{cmd.qualified_name} {cmd.signature}`", inline=False)
            embed.add_field(name="Aliases", value=aliases, inline=False)
            if cmd.brief:
                embed.add_field(name="Resumo", value=cmd.brief, inline=False)
            embed.set_footer(text="TensuraBot • Sistema de Ajuda")
            await ctx.send(embed=embed)
            return

        categorias = {}
        for cmd in sorted(self.bot.commands, key=lambda c: c.name.lower()):
            if cmd.hidden or cmd.name == "help":
                continue
            categoria = self._categoria(cmd.cog)
            categorias.setdefault(categoria, []).append(cmd)

        embed = discord.Embed(
            title="🌙 TensuraBot • Central de Comandos",
            description=(
                "Use os comandos abaixo para acessar os sistemas do bot.\n"
                f"Para detalhes sobre um comando específico, use `{prefixo}help <comando>`."
            ),
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url if self.bot.user else discord.Embed.Empty)

        ordem = ["⚔️ RPG", "💰 Economia", "🛡️ Administração", "📌 Outros"]
        for categoria in ordem:
            comandos = categorias.get(categoria, [])
            if not comandos:
                continue
            texto = " • ".join(f"`{prefixo}{cmd.name}`" for cmd in comandos)
            if len(texto) > 1000:
                texto = texto[:997] + "..."
            embed.add_field(name=f"{categoria} ({len(comandos)})", value=texto, inline=False)

        embed.add_field(
            name="ℹ️ Ajuda rápida",
            value=f"`{prefixo}help <comando>` — informações detalhadas\n`{prefixo}ajuda` — abre este menu",
            inline=False,
        )
        embed.set_footer(text="Tensura Moon • Korczak Technologies")
        await ctx.send(embed=embed)


async def setup(bot):
    bot.remove_command("help")
    await bot.add_cog(Ajuda(bot))
