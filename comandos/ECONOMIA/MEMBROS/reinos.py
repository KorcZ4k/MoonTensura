import discord
from datetime import datetime, timezone
from uuid import uuid4
from discord.ext import commands
from database.python.mongodb import db


NIVEL_MINIMO_REINO = 100


class ReinosMembros(commands.Cog):
    """Assentamentos e reinos vinculados ao ID de cada jogador."""

    def __init__(self, bot):
        self.bot = bot
        self.assentamentos = db["Economia_Assentamentos"]
        self.reinos = db["Economia_Governos"]
        self.tesouros = db["Economia_Tesouros"]
        self.eventos = db["Economia_Eventos"]

    @staticmethod
    def agora():
        return datetime.now(timezone.utc)

    def _assentamento(self, guild_id, owner_id):
        return self.assentamentos.find_one({"guild_id": str(guild_id), "owner_id": str(owner_id), "status": "ativo"})

    def _reino(self, guild_id, owner_id):
        return self.reinos.find_one({"guild_id": str(guild_id), "owner_id": str(owner_id), "tipo": "reino", "status": "ativo"})

    @commands.command(name="assentamento")
    @commands.guild_only()
    async def assentamento(self, ctx, *, nome: str):
        """Cria o primeiro assentamento do jogador, sempre como uma aldeia."""
        existente = self._assentamento(ctx.guild.id, ctx.author.id)
        if existente:
            await ctx.send(
                f"❌ Você já possui a aldeia **{existente['nome']}**. "
                "Use `!reino menu` para consultar seu progresso."
            )
            return

        assentamento_id = f"ass-{uuid4().hex[:12]}"
        agora = self.agora()
        documento = {
            "assentamento_id": assentamento_id,
            "guild_id": str(ctx.guild.id),
            "owner_id": str(ctx.author.id),
            "nome": nome,
            "tipo": "aldeia",
            "status": "ativo",
            "nivel": 1,
            "populacao": 0,
            "reino_id": None,
            "criado_em": agora,
            "atualizado_em": agora,
        }
        self.assentamentos.insert_one(documento)
        self.eventos.insert_one({
            "tipo": "fundacao_assentamento",
            "guild_id": str(ctx.guild.id),
            "owner_id": str(ctx.author.id),
            "assentamento_id": assentamento_id,
            "nome": nome,
            "categoria": "aldeia",
            "criado_em": agora,
        })
        await ctx.send(
            f"🏕️ Sua **Aldeia {nome}** foi fundada!\n"
            f"📈 Nível inicial: **1/100**\n"
            f"👑 Para fundar um reino, sua aldeia precisa alcançar o **nível {NIVEL_MINIMO_REINO}**.\n"
            "Use `!reino menu` para acompanhar seu progresso."
        )

    @commands.group(name="reino", invoke_without_command=True)
    @commands.guild_only()
    async def reino(self, ctx):
        await self.reino_menu(ctx)

    @reino.command(name="menu")
    async def reino_menu(self, ctx):
        reino = self._reino(ctx.guild.id, ctx.author.id)
        assentamento = self._assentamento(ctx.guild.id, ctx.author.id)
        if not reino and not assentamento:
            await ctx.send("🏕️ Você ainda não possui uma aldeia. Use `!assentamento <nome>` para iniciar.")
            return

        embed = discord.Embed(title="🏛️ Menu do Reino", color=discord.Color.gold())
        if assentamento:
            nivel = int(assentamento.get("nivel", 1))
            progresso = min(100, max(0, nivel))
            barra = "█" * (progresso // 10) + "░" * (10 - (progresso // 10))
            embed.add_field(
                name="🏕️ Aldeia",
                value=(
                    f"**{assentamento['nome']}**\n"
                    f"Nível: **{nivel}/{NIVEL_MINIMO_REINO}**\n"
                    f"`{barra}`\n"
                    f"População: **{assentamento.get('populacao', 0):,}**"
                ),
                inline=False,
            )
        if reino:
            tesouro = self.tesouros.find_one({"governo_id": reino["governo_id"]}) or {}
            embed.add_field(
                name="👑 Reino",
                value=(
                    f"**{reino['nome']}**\n"
                    f"ID: `{reino['governo_id']}`\n"
                    f"Status: {reino.get('status', 'ativo')}\n"
                    f"Tesouro: {float(tesouro.get('saldo_bronze', 0)):,.0f} Hunos"
                ),
                inline=False,
            )
        else:
            nivel = int(assentamento.get("nivel", 1)) if assentamento else 0
            faltam = max(0, NIVEL_MINIMO_REINO - nivel)
            embed.add_field(
                name="👑 Fundação do Reino",
                value=(
                    "🔒 Bloqueada até sua aldeia alcançar o nível 100.\n"
                    f"Faltam **{faltam} níveis**."
                ),
                inline=False,
            )
        embed.set_footer(text="Seu reino é vinculado ao seu ID do Discord.")
        await ctx.send(embed=embed)

    @reino.command(name="fundar")
    async def fundar_reino(self, ctx, *, nome: str):
        if self._reino(ctx.guild.id, ctx.author.id):
            await ctx.send("❌ Você já possui um reino ativo neste servidor.")
            return

        assentamento = self._assentamento(ctx.guild.id, ctx.author.id)
        if not assentamento:
            await ctx.send("❌ Primeiro crie uma aldeia com `!assentamento <nome>`.")
            return

        nivel_assentamento = int(assentamento.get("nivel", 1))
        if nivel_assentamento < NIVEL_MINIMO_REINO:
            faltam = NIVEL_MINIMO_REINO - nivel_assentamento
            await ctx.send(
                "🔒 Você ainda não pode fundar um reino.\n"
                f"Sua aldeia está no **nível {nivel_assentamento}/{NIVEL_MINIMO_REINO}**.\n"
                f"Faltam **{faltam} níveis** para desbloquear `!reino fundar`."
            )
            return

        governo_id = f"rei-{uuid4().hex[:12]}"
        agora = self.agora()
        reino = {
            "governo_id": governo_id,
            "guild_id": str(ctx.guild.id),
            "owner_id": str(ctx.author.id),
            "assentamento_id": assentamento["assentamento_id"],
            "nome": nome,
            "tipo": "reino",
            "status": "ativo",
            "autonomia": False,
            "controlado_por_jogador": True,
            "taxas": {"venda": 0.0, "renda": 0.0, "empresa": 0.0, "importacao": 0.0, "exportacao": 0.0, "propriedade": 0.0},
            "tarifas": {"importacao": 0.0, "exportacao": 0.0},
            "criado_em": agora,
            "atualizado_em": agora,
        }
        self.reinos.insert_one(reino)
        self.tesouros.insert_one({
            "governo_id": governo_id,
            "guild_id": str(ctx.guild.id),
            "owner_id": str(ctx.author.id),
            "saldo_bronze": 0.0,
            "receita_total_bronze": 0.0,
            "gasto_total_bronze": 0.0,
            "divida_publica_bronze": 0.0,
            "criado_em": agora,
        })
        self.assentamentos.update_one(
            {"_id": assentamento["_id"]},
            {"$set": {"reino_id": governo_id, "atualizado_em": agora}},
        )
        self.eventos.insert_one({
            "tipo": "fundacao_reino",
            "guild_id": str(ctx.guild.id),
            "owner_id": str(ctx.author.id),
            "governo_id": governo_id,
            "nome": nome,
            "criado_em": agora,
        })
        await ctx.send(
            f"👑 O Reino **{nome}** foi fundado com sucesso!\n"
            f"ID do Reino: `{governo_id}`\n"
            "Use `!reino menu` para ver suas informações."
        )


async def setup(bot):
    await bot.add_cog(ReinosMembros(bot))
