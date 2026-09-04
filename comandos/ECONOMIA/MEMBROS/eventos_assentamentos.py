import asyncio
import random
from datetime import datetime, timezone
from uuid import uuid4

import discord
from discord.ext import commands

from database.python.mongodb import db

INTERVALO_SEGUNDOS = 60
CHANCE_EVENTO_POR_TERRITORIO = 0.35
STATUS_NAO_RESOLVIDOS = ["ativo", "pendente", "combate"]


class EventosAssentamentos(commands.Cog):
    """Gera e administra acontecimentos autônomos dos assentamentos."""

    def __init__(self, bot):
        self.bot = bot
        self.assentamentos = db["Economia_Assentamentos"]
        self.eventos = db["Economia_Eventos_Assentamentos"]
        self._tarefa = None
        self._ativo = False

    @staticmethod
    def agora():
        return datetime.now(timezone.utc)

    @staticmethod
    def escolher_evento(assentamento):
        nivel = int(assentamento.get("nivel", 1))
        opcoes = [
            ("refugiados", 30),
            ("bandidos", 25),
            ("monstro", 20),
            ("mercador", 10),
            ("viajantes", 8),
            ("recurso", 7),
        ]
        if nivel >= 25:
            opcoes.append(("caravana", 8))
        if nivel >= 50:
            opcoes.append(("ameaca_territorial", 8))
        tipos, pesos = zip(*opcoes)
        return random.choices(tipos, weights=pesos, k=1)[0]

    @staticmethod
    def dados_evento(tipo, assentamento):
        nome = assentamento.get("nome", "assentamento")
        if tipo == "refugiados":
            quantidade = random.randint(1, max(3, int(assentamento.get("nivel", 1)) // 2 + 2))
            return {
                "titulo": "🏕️ Refugiados chegaram",
                "descricao": f"Um grupo de **{quantidade} refugiados** chegou aos arredores de **{nome}** procurando abrigo e proteção.",
                "cor": discord.Color.green(), "hostil": False,
                "dados": {"quantidade": quantidade},
            }
        if tipo == "bandidos":
            quantidade = random.randint(2, 8 + int(assentamento.get("nivel", 1)) // 10)
            return {
                "titulo": "⚔️ Bandidos avistados",
                "descricao": f"Um grupo de aproximadamente **{quantidade} bandidos** foi avistado próximo ao território de **{nome}**.",
                "cor": discord.Color.red(), "hostil": True,
                "dados": {"quantidade": quantidade},
            }
        if tipo == "monstro":
            nivel = int(assentamento.get("nivel", 1))
            ameaca = random.choice(["baixa", "moderada", "alta"] if nivel >= 30 else ["baixa", "moderada"])
            return {
                "titulo": "👹 Criatura hostil detectada",
                "descricao": f"Uma criatura de ameaça **{ameaca}** entrou ou se aproximou do território de **{nome}**.",
                "cor": discord.Color.dark_red(), "hostil": True,
                "dados": {"ameaca": ameaca},
            }
        if tipo == "mercador":
            return {"titulo": "🛒 Mercador itinerante", "descricao": f"Um mercador itinerante chegou ao território de **{nome}** oferecendo mercadorias e procurando oportunidades de comércio.", "cor": discord.Color.gold(), "hostil": False, "dados": {}}
        if tipo == "viajantes":
            return {"titulo": "🚶 Viajantes no território", "descricao": f"Viajantes atravessam o território de **{nome}**. Eles podem trazer notícias, oportunidades ou problemas.", "cor": discord.Color.blue(), "hostil": False, "dados": {}}
        if tipo == "recurso":
            recurso = random.choice(["madeira", "pedra", "água", "minério", "ervas"])
            return {"titulo": "🌿 Recurso descoberto", "descricao": f"Habitantes de **{nome}** encontraram uma possível fonte de **{recurso}** dentro ou perto do território.", "cor": discord.Color.teal(), "hostil": False, "dados": {"recurso": recurso}}
        if tipo == "caravana":
            return {"titulo": "🐎 Caravana chegou", "descricao": f"Uma caravana comercial alcançou o território de **{nome}**, trazendo pessoas, mercadorias e possíveis contatos comerciais.", "cor": discord.Color.orange(), "hostil": False, "dados": {}}
        return {"titulo": "⚠️ Ameaça territorial", "descricao": f"Uma situação incomum e potencialmente perigosa foi identificada nas proximidades de **{nome}**.", "cor": discord.Color.dark_orange(), "hostil": True, "dados": {}}

    def possui_evento_pendente(self, assentamento_id):
        return self.eventos.find_one({
            "assentamento_id": str(assentamento_id),
            "status": {"$in": STATUS_NAO_RESOLVIDOS},
        })

    def jogador_pertence_ao_assentamento(self, interaction, evento):
        if str(interaction.user.id) == str(evento.get("owner_id")):
            return True
        assentamento = self.assentamentos.find_one({"assentamento_id": evento.get("assentamento_id")})
        if not assentamento:
            return False
        membros = [str(x) for x in assentamento.get("membros", [])]
        return str(interaction.user.id) in membros

    async def iniciar_combate(self, interaction, evento_id):
        evento = self.eventos.find_one({"evento_id": evento_id})
        if not evento:
            await interaction.response.send_message("❌ Este evento não existe mais.", ephemeral=True)
            return
        if not evento.get("hostil"):
            await interaction.response.send_message("❌ Este evento não pode ser resolvido através de combate.", ephemeral=True)
            return
        if evento.get("status") in {"resolvido", "fracassado"}:
            await interaction.response.send_message("❌ Este evento já foi encerrado.", ephemeral=True)
            return
        if not self.jogador_pertence_ao_assentamento(interaction, evento):
            await interaction.response.send_message("❌ Apenas o responsável ou membros registrados do assentamento podem iniciar esta luta.", ephemeral=True)
            return

        resultado = self.eventos.update_one(
            {"evento_id": evento_id, "status": {"$in": ["ativo", "pendente"]}},
            {"$set": {
                "status": "combate",
                "combatente_id": str(interaction.user.id),
                "combate_iniciado_em": self.agora(),
            }},
        )
        if resultado.modified_count == 0:
            await interaction.response.send_message("⚔️ Este evento já está em combate ou foi resolvido.", ephemeral=True)
            return

        embed = discord.Embed(
            title="⚔️ Combate iniciado",
            description=f"{interaction.user.mention} decidiu enfrentar a ameaça do evento `{evento_id}`.",
            color=discord.Color.red(),
            timestamp=self.agora(),
        )
        embed.add_field(name="📌 Situação", value="⚔️ Em combate", inline=True)
        embed.set_footer(text="O evento continua bloqueando novos acontecimentos até ser resolvido.")
        await interaction.response.send_message(embed=embed)

    async def resolver_evento(self, ctx, evento, resultado):
        status = "resolvido" if resultado == "vitoria" else "fracassado"
        self.eventos.update_one(
            {"_id": evento["_id"]},
            {"$set": {"status": status, "resultado": resultado, "resolvido_em": self.agora(), "resolvido_por": str(ctx.author.id)}},
        )
        cor = discord.Color.green() if status == "resolvido" else discord.Color.dark_red()
        titulo = "🏆 Evento resolvido" if status == "resolvido" else "💀 Evento fracassado"
        embed = discord.Embed(title=titulo, color=cor, timestamp=self.agora())
        embed.add_field(name="🆔 Evento", value=f"`{evento['evento_id']}`", inline=False)
        embed.add_field(name="Resultado", value="Vitória" if resultado == "vitoria" else "Fracasso", inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="evento_lutar")
    @commands.guild_only()
    async def evento_lutar(self, ctx, evento_id: str):
        evento = self.eventos.find_one({"evento_id": evento_id})
        if not evento:
            await ctx.send("❌ Evento não encontrado.")
            return
        if not evento.get("hostil"):
            await ctx.send("❌ Este evento não é uma ameaça combatível.")
            return
        if str(ctx.author.id) != str(evento.get("owner_id")):
            assentamento = self.assentamentos.find_one({"assentamento_id": evento.get("assentamento_id")}) or {}
            membros = [str(x) for x in assentamento.get("membros", [])]
            if str(ctx.author.id) not in membros:
                await ctx.send("❌ Você não pertence a este assentamento.")
                return
        resultado = self.eventos.update_one(
            {"evento_id": evento_id, "status": {"$in": ["ativo", "pendente"]}},
            {"$set": {"status": "combate", "combatente_id": str(ctx.author.id), "combate_iniciado_em": self.agora()}},
        )
        if resultado.modified_count == 0:
            await ctx.send("❌ Este evento já está em combate ou foi encerrado.")
            return
        await ctx.send(f"⚔️ {ctx.author.mention} iniciou a luta contra a ameaça do evento `{evento_id}`.")

    @commands.command(name="evento_resolver")
    @commands.guild_only()
    async def evento_resolver(self, ctx, evento_id: str, resultado: str):
        evento = self.eventos.find_one({"evento_id": evento_id})
        if not evento:
            await ctx.send("❌ Evento não encontrado.")
            return
        if str(ctx.author.id) != str(evento.get("owner_id")):
            await ctx.send("❌ Apenas o responsável pelo assentamento pode encerrar este evento.")
            return
        resultado = resultado.lower().strip()
        if resultado not in {"vitoria", "derrota"}:
            await ctx.send("❌ Use `!evento_resolver <id> vitoria` ou `!evento_resolver <id> derrota`.")
            return
        await self.resolver_evento(ctx, evento, resultado)

    async def processar_assentamento(self, assentamento):
        # Regra principal: um evento pendente bloqueia qualquer novo evento.
        pendente = self.possui_evento_pendente(assentamento["assentamento_id"])
        if pendente:
            return 0

        territorios = list(assentamento.get("territorios", []))
        if not territorios:
            return 0

        # Apenas um evento por ciclo e por assentamento.
        canal_id = random.choice(territorios)
        if random.random() > CHANCE_EVENTO_POR_TERRITORIO:
            return 0
        canal = self.bot.get_channel(int(canal_id))
        if canal is None or not hasattr(canal, "send"):
            return 0

        tipo = self.escolher_evento(assentamento)
        evento = self.dados_evento(tipo, assentamento)
        evento_id = f"evt-ass-{uuid4().hex[:12]}"
        agora = self.agora()
        documento = {
            "evento_id": evento_id,
            "tipo": tipo,
            "guild_id": str(assentamento["guild_id"]),
            "owner_id": str(assentamento["owner_id"]),
            "assentamento_id": assentamento["assentamento_id"],
            "canal_id": str(canal_id),
            "status": "ativo",
            "hostil": evento["hostil"],
            "dados": evento["dados"],
            "criado_em": agora,
        }
        self.eventos.insert_one(documento)

        embed = discord.Embed(title=evento["titulo"], description=evento["descricao"], color=evento["cor"], timestamp=agora)
        embed.add_field(name="🏕️ Assentamento", value=assentamento.get("nome", "Desconhecido"), inline=True)
        embed.add_field(name="🆔 Evento", value=f"`{evento_id}`", inline=True)
        embed.add_field(name="📌 Situação", value="⚔️ Ameaça ativa" if evento["hostil"] else "⏳ Aguardando resolução", inline=True)

        view = None
        if evento["hostil"]:
            view = discord.ui.View(timeout=None)
            botao = discord.ui.Button(label="⚔️ Lutar", style=discord.ButtonStyle.danger, custom_id=f"evento_lutar:{evento_id}")

            async def callback(interaction, identificador=evento_id):
                await self.iniciar_combate(interaction, identificador)

            botao.callback = callback
            view.add_item(botao)
            embed.add_field(name="⚔️ Combate", value="Clique em **Lutar** para iniciar o confronto.", inline=False)
        else:
            embed.add_field(name="⏳ Regra", value="Nenhum novo evento surgirá para este assentamento até este acontecimento ser resolvido.", inline=False)

        embed.set_footer(text="Um assentamento só pode possuir um evento não resolvido por vez.")
        try:
            await canal.send(embed=embed, view=view)
            return 1
        except (discord.Forbidden, discord.HTTPException) as erro:
            self.eventos.update_one({"evento_id": evento_id}, {"$set": {"status": "erro_envio", "erro": str(erro)}})
            print(f"[EVENTOS][ERRO] Canal {canal_id}: {erro}")
            return 0

    async def executar_ciclo(self):
        total = 0
        bloqueados = 0
        for assentamento in self.assentamentos.find({"status": "ativo"}):
            try:
                if self.possui_evento_pendente(assentamento["assentamento_id"]):
                    bloqueados += 1
                    continue
                total += await self.processar_assentamento(assentamento)
            except Exception as erro:
                print(f"[EVENTOS][ERRO] Assentamento {assentamento.get('assentamento_id')}: {erro}")
        print(f"🏕️ Ciclo de eventos: {total} gerados | {bloqueados} assentamentos com evento pendente.")

    async def loop_eventos(self):
        while self._ativo:
            await asyncio.sleep(INTERVALO_SEGUNDOS)
            await self.executar_ciclo()

    @commands.Cog.listener()
    async def on_ready(self):
        if self._ativo:
            return
        self._ativo = True
        self._tarefa = asyncio.create_task(self.loop_eventos())
        print(f"🏕️ Eventos automáticos de assentamentos iniciados: intervalo de {INTERVALO_SEGUNDOS} segundos.")

    def cog_unload(self):
        self._ativo = False
        if self._tarefa:
            self._tarefa.cancel()


async def setup(bot):
    await bot.add_cog(EventosAssentamentos(bot))
