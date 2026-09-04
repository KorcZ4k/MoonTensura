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

    @staticmethod
    def _territorios(documento):
        return [str(x) for x in documento.get("territorios", [])]

    @staticmethod
    def _formatar_hunos(valor):
        return f"{float(valor):,.0f} Hunos".replace(",", ".")

    @commands.command(name="assentamento")
    @commands.guild_only()
    async def assentamento(self, ctx, *, nome: str):
        """Cria o primeiro assentamento do jogador, sempre como uma aldeia."""
        existente = self._assentamento(ctx.guild.id, ctx.author.id)
        if existente:
            embed = discord.Embed(
                title="❌ Assentamento já existente",
                description=(
                    f"Você já possui a aldeia **{existente['nome']}**.\n"
                    "Use `!reino menu` para consultar seu progresso."
                ),
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

        assentamento_id = f"ass-{uuid4().hex[:12]}"
        agora = self.agora()
        documento = {
            "assentamento_id": assentamento_id,
            "guild_id": str(ctx.guild.id),
            "owner_id": str(ctx.author.id),
            "fundador_id": str(ctx.author.id),
            "chefe_vila_id": str(ctx.author.id),
            "nome": nome,
            "tipo": "aldeia",
            "status": "ativo",
            "nivel": 1,
            "populacao": 0,
            "territorios": [str(ctx.channel.id)],
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
            "canal_id": str(ctx.channel.id),
            "criado_em": agora,
        })

        embed = discord.Embed(
            title="🏕️ Aldeia fundada",
            description=f"A **Aldeia {nome}** foi oficialmente fundada.",
            color=discord.Color.green(),
            timestamp=agora,
        )
        embed.add_field(name="📈 Nível", value=f"**1/{NIVEL_MINIMO_REINO}**", inline=True)
        embed.add_field(name="👑 Chefe da Vila", value=ctx.author.mention, inline=True)
        embed.add_field(name="🗺️ Território inicial", value=ctx.channel.mention, inline=False)
        embed.add_field(
            name="🔒 Fundação do Reino",
            value=f"Alcance o **nível {NIVEL_MINIMO_REINO}** para desbloquear `!reino fundar <nome>`.",
            inline=False,
        )
        embed.set_footer(text="Use !reino menu para acompanhar seu território.")
        await ctx.send(embed=embed)

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

        fundador_id = str((reino or assentamento).get("fundador_id") or (reino or assentamento).get("owner_id"))
        chefe_id = str(assentamento.get("chefe_vila_id") or assentamento.get("owner_id")) if assentamento else fundador_id
        territorios_assentamento = self._territorios(assentamento) if assentamento else []
        territorios_reino = self._territorios(reino) if reino else []
        tamanho_total = len(set(territorios_assentamento + territorios_reino))
        populacao = int((reino or {}).get("populacao", assentamento.get("populacao", 0))) if assentamento else int(reino.get("populacao", 0))

        tesouro_valor = 0.0
        if reino:
            tesouro = self.tesouros.find_one({"governo_id": reino["governo_id"]}) or {}
            tesouro_valor = float(tesouro.get("saldo_bronze", 0))

        embed = discord.Embed(
            title=f"🏛️ {reino['nome'] if reino else assentamento['nome']}",
            color=discord.Color.gold() if reino else discord.Color.green(),
        )
        embed.add_field(name="👤 Fundador", value=f"<@{fundador_id}>", inline=True)
        embed.add_field(name="👑 Chefe da Vila", value=f"<@{chefe_id}>", inline=True)
        embed.add_field(name="👥 População", value=f"**{populacao:,}**", inline=True)
        embed.add_field(name="💰 Tesouro", value=f"**{self._formatar_hunos(tesouro_valor)}**", inline=True)
        embed.add_field(name="🗺️ Tamanho", value=f"**{tamanho_total} chat(s)**", inline=True)

        if assentamento:
            nivel = int(assentamento.get("nivel", 1))
            progresso = min(100, max(0, nivel))
            barra = "█" * (progresso // 10) + "░" * (10 - (progresso // 10))
            embed.add_field(
                name="🏕️ Assentamento",
                value=f"**Aldeia {assentamento['nome']}**\nNível: **{nivel}/{NIVEL_MINIMO_REINO}**\n`{barra}`",
                inline=False,
            )
        if reino:
            embed.add_field(
                name="🏰 Reino",
                value=f"**{reino['nome']}**\nID: `{reino['governo_id']}`\nStatus: **{reino.get('status', 'ativo')}**",
                inline=False,
            )
        else:
            nivel = int(assentamento.get("nivel", 1))
            faltam = max(0, NIVEL_MINIMO_REINO - nivel)
            embed.add_field(
                name="🔒 Fundação do Reino",
                value=f"Sua aldeia precisa chegar ao nível **100**. Faltam **{faltam} níveis**.",
                inline=False,
            )
        embed.set_footer(text="Use !expandir neste chat para adicioná-lo ao seu território.")
        await ctx.send(embed=embed)

    @commands.command(name="expandir")
    @commands.guild_only()
    async def expandir(self, ctx, alvo: str = None):
        """Adiciona o chat atual ao território do assentamento ou reino do jogador."""
        alvo = (alvo or "").lower().strip()
        reino = self._reino(ctx.guild.id, ctx.author.id)
        assentamento = self._assentamento(ctx.guild.id, ctx.author.id)

        if not assentamento:
            await ctx.send("❌ Primeiro crie sua aldeia com `!assentamento <nome>`.")
            return

        if alvo and alvo not in {"assentamento", "aldeia", "reino"}:
            await ctx.send("❌ Use `!expandir`, `!expandir assentamento` ou `!expandir reino`.")
            return
        if alvo == "reino" and not reino:
            await ctx.send("❌ Você ainda não possui um reino para expandir.")
            return

        documento = reino if (reino and alvo == "reino") else assentamento
        colecao = self.reinos if documento is reino else self.assentamentos
        campo_id = "governo_id" if documento is reino else "assentamento_id"
        chat_id = str(ctx.channel.id)
        territorios = self._territorios(documento)

        if chat_id in territorios:
            await ctx.send("❌ Este chat já pertence ao seu território.")
            return

        colecao.update_one(
            {campo_id: documento[campo_id]},
            {"$addToSet": {"territorios": chat_id}, "$set": {"atualizado_em": self.agora()}},
        )
        self.eventos.insert_one({
            "tipo": "expansao_territorial",
            "guild_id": str(ctx.guild.id),
            "owner_id": str(ctx.author.id),
            "alvo": "reino" if documento is reino else "assentamento",
            "canal_id": chat_id,
            "criado_em": self.agora(),
        })
        await ctx.send(f"🗺️ **{ctx.channel.name}** foi adicionado ao território do seu {'reino' if documento is reino else 'assentamento'}.")

    @commands.command(name="abandonar_territorio", aliases=["abandonar"])
    @commands.guild_only()
    async def abandonar_territorio(self, ctx, alvo: str = None):
        """Remove o chat atual do território do assentamento ou reino."""
        alvo = (alvo or "").lower().strip()
        reino = self._reino(ctx.guild.id, ctx.author.id)
        assentamento = self._assentamento(ctx.guild.id, ctx.author.id)
        chat_id = str(ctx.channel.id)

        if not assentamento:
            await ctx.send("❌ Você não possui um território para abandonar.")
            return

        if alvo and alvo not in {"assentamento", "aldeia", "reino"}:
            await ctx.send("❌ Use `!abandonar_territorio`, `!abandonar_territorio assentamento` ou `!abandonar_territorio reino`.")
            return

        if alvo == "reino":
            documentos = [(self.reinos, reino, "governo_id", "reino")] if reino else []
        elif alvo in {"assentamento", "aldeia"}:
            documentos = [(self.assentamentos, assentamento, "assentamento_id", "assentamento")]
        else:
            documentos = [(self.reinos, reino, "governo_id", "reino")] if reino and chat_id in self._territorios(reino) else []
            if not documentos:
                documentos = [(self.assentamentos, assentamento, "assentamento_id", "assentamento")]

        for colecao, documento, campo_id, tipo in documentos:
            if not documento or chat_id not in self._territorios(documento):
                continue
            territorios = self._territorios(documento)
            if len(territorios) <= 1:
                await ctx.send("❌ Você não pode abandonar o último chat do seu território.")
                return
            colecao.update_one(
                {campo_id: documento[campo_id]},
                {"$pull": {"territorios": chat_id}, "$set": {"atualizado_em": self.agora()}},
            )
            self.eventos.insert_one({
                "tipo": "abandono_territorial",
                "guild_id": str(ctx.guild.id),
                "owner_id": str(ctx.author.id),
                "alvo": tipo,
                "canal_id": chat_id,
                "criado_em": self.agora(),
            })
            await ctx.send(f"🏳️ **{ctx.channel.name}** foi abandonado e removido do território do seu {tipo}.")
            return

        await ctx.send("❌ Este chat não pertence ao território selecionado.")

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
            await ctx.send(f"🔒 Reino bloqueado. Aldeia: **{nivel_assentamento}/100**. Faltam **{faltam} níveis**.")
            return

        governo_id = f"rei-{uuid4().hex[:12]}"
        agora = self.agora()
        reino = {
            "governo_id": governo_id,
            "guild_id": str(ctx.guild.id),
            "owner_id": str(ctx.author.id),
            "fundador_id": str(ctx.author.id),
            "assentamento_id": assentamento["assentamento_id"],
            "nome": nome,
            "tipo": "reino",
            "status": "ativo",
            "populacao": int(assentamento.get("populacao", 0)),
            "territorios": [],
            "autonomia": False,
            "controlado_por_jogador": True,
            "taxas": {"venda": 0.0, "renda": 0.0, "empresa": 0.0, "importacao": 0.0, "exportacao": 0.0, "propriedade": 0.0},
            "tarifas": {"importacao": 0.0, "exportacao": 0.0},
            "criado_em": agora,
            "atualizado_em": agora,
        }
        self.reinos.insert_one(reino)
        self.tesouros.insert_one({"governo_id": governo_id, "guild_id": str(ctx.guild.id), "owner_id": str(ctx.author.id), "saldo_bronze": 0.0, "receita_total_bronze": 0.0, "gasto_total_bronze": 0.0, "divida_publica_bronze": 0.0, "criado_em": agora})
        self.assentamentos.update_one({"_id": assentamento["_id"]}, {"$set": {"reino_id": governo_id, "atualizado_em": agora}})
        self.eventos.insert_one({"tipo": "fundacao_reino", "guild_id": str(ctx.guild.id), "owner_id": str(ctx.author.id), "governo_id": governo_id, "nome": nome, "criado_em": agora})

        embed = discord.Embed(title="👑 Reino fundado", description=f"O Reino **{nome}** foi oficialmente fundado!", color=discord.Color.gold(), timestamp=agora)
        embed.add_field(name="👤 Fundador", value=ctx.author.mention, inline=True)
        embed.add_field(name="🏕️ Aldeia de origem", value=assentamento["nome"], inline=True)
        embed.add_field(name="🆔 ID do Reino", value=f"`{governo_id}`", inline=False)
        embed.set_footer(text="Use !reino menu para consultar as informações do seu território.")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ReinosMembros(bot))
