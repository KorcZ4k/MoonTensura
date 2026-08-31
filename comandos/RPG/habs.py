import discord
from discord.ext import commands

# Ordem de exibição das raridades no embed
ORDEM_RARIDADES = ["Comum", "Única", "Raça", "Definitiva", "Suprema", "Extra"]

# Cor por raridade (opcional, deixa o embed mais bonito)
COR_RARIDADE = {
    "Comum": 0x95a5a6,
    "Única": 0x3498db,
    "Raça": 0x2ecc71,
    "Definitiva": 0x9b59b6,
    "Suprema": 0xe67e22,
    "Extra": 0xe74c3c,
}


class Habilidades(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db  # ajuste conforme como você acessa o mongo (ex: self.bot.mongo_client["seu_db"])

    @commands.command(name="habilidades", aliases=["habs", "habils", "skills"])
    async def habs(self, ctx: commands.Context):
        jogadores = self.db["Jogadores"]      # coleção dos jogadores (ajuste o nome se for diferente)
        habilidades = self.db["Habilidades"]  # coleção com o catálogo de habilidades

        jogador = jogadores.find_one({
            "user_id": ctx.author.id,
            "guild_id": ctx.guild.id
        })

        if not jogador or not jogador.get("habs"):
            await ctx.send("Você ainda não possui nenhuma habilidade.")
            return

        ids_do_jogador = jogador["habs"]  # lista de strings tipo "00001"

        # busca todas as habilidades do jogador de uma vez só (mais eficiente que N queries)
        cursor = habilidades.find({"id": {"$in": ids_do_jogador}})

        # agrupa por raridade
        agrupado = {}
        for hab in cursor:
            raridade = hab.get("raridade", "Outras")
            agrupado.setdefault(raridade, []).append(hab)

        if not agrupado:
            await ctx.send("Não encontrei suas habilidades no catálogo. Verifique os IDs salvos.")
            return

        embed = discord.Embed(
            title=f"📖 Catálogo de Habilidades — {ctx.author.display_name}",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        # exibe respeitando a ordem definida, e qualquer raridade "extra" que não esteja na lista vai no final
        raridades_presentes = list(agrupado.keys())
        ordem_final = [r for r in ORDEM_RARIDADES if r in agrupado] + \
                      [r for r in raridades_presentes if r not in ORDEM_RARIDADES]

        for raridade in ordem_final:
            lista = agrupado[raridade]
            texto = "\n".join(f"`{h['id']}` **{h['nome']}**" for h in lista)
            # embed tem limite de 1024 caracteres por field
            if len(texto) > 1024:
                texto = texto[:1000] + "\n... (lista truncada)"
            embed.add_field(
                name=f"{raridade} ({len(lista)})",
                value=texto,
                inline=False
            )

        embed.set_footer(text=f"Total de habilidades: {len(ids_do_jogador)}")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Habilidades(bot))