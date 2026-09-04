import asyncio
import random
from datetime import datetime, timezone
from uuid import uuid4

import discord
from discord.ext import commands
from database.python.mongodb import db

INTERVALO_SEGUNDOS = 60
CHANCE_EVENTO = 0.35
STATUS_BLOQUEADORES = {"aceito", "combate"}

RECURSOS_INICIAIS = [
    "madeira", "pedras", "tijolos", "argila", "cimento", "ferro", "metal", "aco",
    "carne", "peixe", "graos", "trigo", "arroz", "milho", "leite", "ovos",
    "areia", "vidro", "cobre", "bronze", "prata", "ouro", "carvao", "agua",
    "ervas", "couro", "la", "algodao", "tecido", "papel", "ferramentas",
]


class EventosAssentamentos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.assentamentos = db["Economia_Assentamentos"]
        self.eventos = db["Economia_Eventos_Assentamentos"]
        self._tarefa = None
        self._ativo = False

    @staticmethod
    def agora():
        return datetime.now(timezone.utc)

    def garantir_dados_assentamento(self, assentamento):
        """Mantém recursos e informações econômicas dentro do próprio documento do assentamento."""
        recursos = assentamento.get("recursos", {})
        alteracoes = {}
        for recurso in RECURSOS_INICIAIS:
            if recurso not in recursos:
                recursos[recurso] = 0
        if assentamento.get("recursos") != recursos:
            alteracoes["recursos"] = recursos
        if "estoque_armas" not in assentamento:
            alteracoes["estoque_armas"] = {}
        if "edificios_construidos" not in assentamento:
            alteracoes["edificios_construidos"] = {}
        if "edificios_em_construcao" not in assentamento:
            alteracoes["edificios_em_construcao"] = {}
        if "xp_eventos_multiplicador" not in assentamento:
            alteracoes["xp_eventos_multiplicador"] = 1.0
        if "xp_eventos_perdido_percentual" not in assentamento:
            alteracoes["xp_eventos_perdido_percentual"] = 0.0
        if alteracoes:
            alteracoes["atualizado_em"] = self.agora()
            self.assentamentos.update_one({"_id": assentamento["_id"]}, {"$set": alteracoes})
            assentamento.update(alteracoes)
        return assentamento

    @staticmethod
    def escolher_evento():
        tipos = ["refugiados", "bandidos", "monstro", "mercador", "viajantes", "recurso", "caravana"]
        pesos = [30, 25, 20, 10, 8, 7, 8]
        return random.choices(tipos, weights=pesos, k=1)[0]

    def dados_evento(self, tipo, assentamento):
        nome = assentamento.get("nome", "assentamento")
        nivel = int(assentamento.get("nivel", 1))
        if tipo == "refugiados":
            # Fibonacci: 1, 1, 2, 3, 5, 8...
            a, b = 1, 1
            for _ in range(max(0, nivel - 2)):
                a, b = b, a + b
            quantidade = 1 if nivel <= 2 else b
            return "🏕️ Refugiados chegaram", f"**{quantidade} refugiado(s)** chegaram aos arredores de **{nome}**.", discord.Color.green(), False, {"quantidade": quantidade}
        if tipo == "bandidos":
            return "⚔️ Bandidos avistados", f"Um grupo de bandidos foi avistado próximo ao território de **{nome}**.", discord.Color.red(), True, {"nivel_assentamento": nivel}
        if tipo == "monstro":
            nivel_monstro = 1 if nivel <= 2 else nivel - 1
            return "👹 Monstro hostil detectado", f"Uma criatura hostil foi detectada próximo a **{nome}**.", discord.Color.dark_red(), True, {"nivel_monstro": nivel_monstro}
        if tipo == "mercador":
            variacao = random.choice([-10, 10])
            return "🛒 Mercador itinerante", f"Um mercador chegou oferecendo produtos com preços **{abs(variacao)}% {'menores' if variacao < 0 else 'maiores'}** que o mercado.", discord.Color.gold(), False, {"variacao_preco": variacao}
        if tipo == "viajantes":
            destino = random.choice(["bronze", "recurso", "populacao"])
            return "🚶 Viajantes no território", f"Viajantes chegaram ao território de **{nome}**. O resultado dependerá de suas escolhas e circunstâncias.", discord.Color.blue(), False, {"possivel_resultado": destino}
        if tipo == "recurso":
            recurso = random.choice(RECURSOS_INICIAIS)
            utilizavel = random.choice([True, False])
            return "🌿 Descoberta de recurso", f"Uma possível fonte de **{recurso}** foi encontrada perto de **{nome}**.", discord.Color.teal(), False, {"recurso": recurso, "utilizavel": utilizavel}
        return "🐎 Caravana chegou", f"Uma caravana comercial chegou ao território de **{nome}** e pode abrir uma loja temporária neste chat.", discord.Color.orange(), False, {}

    def jogador_autorizado(self, user_id, evento):
        if str(user_id) == str(evento.get("owner_id")):
            return True
        assentamento = self.assentamentos.find_one({"assentamento_id": evento.get("assentamento_id")}) or {}
        return str(user_id) in [str(x) for x in assentamento.get("membros", [])]

    def evento_bloqueador(self, assentamento_id):
        return self.eventos.find_one({"assentamento_id": str(assentamento_id), "status": {"$in": list(STATUS_BLOQUEADORES)}})

    def evento_aguardando(self, assentamento_id):
        return self.eventos.find_one({"assentamento_id": str(assentamento_id), "status": "aguardando"}, sort=[("criado_em", -1)])

    async def responder_evento(self, interaction, evento_id, acao):
        evento = self.eventos.find_one({"evento_id": evento_id})
        if not evento or evento.get("status") != "aguardando":
            await interaction.response.send_message("❌ Este evento não está mais aguardando uma decisão.", ephemeral=True)
            return
        if not self.jogador_autorizado(interaction.user.id, evento):
            await interaction.response.send_message("❌ Você não pertence a este assentamento.", ephemeral=True)
            return

        agora = self.agora()
        if acao == "recusar":
            novo_status = "recusado"
        elif acao == "lutar":
            if not evento.get("hostil"):
                await interaction.response.send_message("❌ Este evento não possui uma ameaça para enfrentar.", ephemeral=True)
                return
            novo_status = "combate"
        else:
            novo_status = "aceito"

        campos = {"status": novo_status, "respondido_por": str(interaction.user.id), "respondido_em": agora}
        if novo_status == "combate":
            campos["combatente_id"] = str(interaction.user.id)
            campos["combate_iniciado_em"] = agora
        resultado = self.eventos.update_one({"evento_id": evento_id, "status": "aguardando"}, {"$set": campos})
        if resultado.modified_count == 0:
            await interaction.response.send_message("❌ Este evento já foi alterado por outra ação.", ephemeral=True)
            return

        mensagens = {
            "recusar": "❌ O evento foi recusado e encerrado.",
            "aceitar": "✅ Evento aceito. Nenhum novo evento aparecerá até ele ser resolvido.",
            "lutar": "⚔️ Combate iniciado. Nenhum novo evento aparecerá até o confronto ser resolvido.",
        }
        await interaction.response.send_message(mensagens[acao], ephemeral=False)

    def criar_view(self, evento_id, hostil):
        view = discord.ui.View(timeout=None)
        for texto, estilo, acao in [
            ("✅ Aceitar", discord.ButtonStyle.success, "aceitar"),
            ("❌ Recusar", discord.ButtonStyle.secondary, "recusar"),
        ]:
            botao = discord.ui.Button(label=texto, style=estilo, custom_id=f"ass_evento:{acao}:{evento_id}")
            async def callback(interaction, identificador=evento_id, escolha=acao):
                await self.responder_evento(interaction, identificador, escolha)
            botao.callback = callback
            view.add_item(botao)
        if hostil:
            lutar = discord.ui.Button(label="⚔️ Lutar", style=discord.ButtonStyle.danger, custom_id=f"ass_evento:lutar:{evento_id}")
            async def callback_lutar(interaction, identificador=evento_id):
                await self.responder_evento(interaction, identificador, "lutar")
            lutar.callback = callback_lutar
            view.add_item(lutar)
        return view

    async def expirar_evento_ignorado(self, assentamento, evento):
        agora = self.agora()
        multiplicador_atual = max(0.0, float(assentamento.get("xp_eventos_multiplicador", 1.0)))
        novo_multiplicador = max(0.0, multiplicador_atual * 0.99)
        perdido = min(100.0, float(assentamento.get("xp_eventos_perdido_percentual", 0.0)) + 1.0)
        self.eventos.update_one({"_id": evento["_id"]}, {"$set": {"status": "ignorado", "ignorado_em": agora}})
        self.assentamentos.update_one({"_id": assentamento["_id"]}, {"$set": {"xp_eventos_multiplicador": novo_multiplicador, "xp_eventos_perdido_percentual": perdido, "atualizado_em": agora}})
        assentamento["xp_eventos_multiplicador"] = novo_multiplicador
        assentamento["xp_eventos_perdido_percentual"] = perdido

    async def processar_assentamento(self, assentamento):
        assentamento = self.garantir_dados_assentamento(assentamento)
        bloqueador = self.evento_bloqueador(assentamento["assentamento_id"])
        if bloqueador:
            return "bloqueado"

        aguardando = self.evento_aguardando(assentamento["assentamento_id"])
        if aguardando:
            criado = aguardando.get("criado_em")
            if criado and (self.agora() - criado).total_seconds() < INTERVALO_SEGUNDOS:
                return "aguardando"
            await self.expirar_evento_ignorado(assentamento, aguardando)

        territorios = list(assentamento.get("territorios", []))
        if not territorios or random.random() > CHANCE_EVENTO:
            return "nenhum"
        canal = self.bot.get_channel(int(random.choice(territorios)))
        if canal is None or not hasattr(canal, "send"):
            return "nenhum"

        tipo = self.escolher_evento()
        titulo, descricao, cor, hostil, dados = self.dados_evento(tipo, assentamento)
        evento_id = f"evt-ass-{uuid4().hex[:12]}"
        agora = self.agora()
        documento = {
            "evento_id": evento_id, "tipo": tipo,
            "guild_id": str(assentamento["guild_id"]), "owner_id": str(assentamento["owner_id"]),
            "assentamento_id": assentamento["assentamento_id"], "canal_id": str(canal.id),
            "status": "aguardando", "hostil": hostil, "dados": dados,
            "xp_multiplicador": max(0.0, float(assentamento.get("xp_eventos_multiplicador", 1.0))),
            "criado_em": agora,
        }
        self.eventos.insert_one(documento)

        embed = discord.Embed(title=titulo, description=descricao, color=cor, timestamp=agora)
        embed.add_field(name="🏕️ Assentamento", value=assentamento.get("nome", "Desconhecido"), inline=True)
        embed.add_field(name="🆔 Evento", value=f"`{evento_id}`", inline=True)
        embed.add_field(name="⏱️ Decisão", value="Você tem 60 segundos para aceitar ou recusar.", inline=False)
        if hostil:
            embed.add_field(name="⚔️ Ameaça", value="Também é possível clicar em **Lutar**.", inline=False)
        await canal.send(embed=embed, view=self.criar_view(evento_id, hostil))
        return "gerado"

    @commands.command(name="evento_lutar")
    @commands.guild_only()
    async def evento_lutar(self, ctx, evento_id: str):
        evento = self.eventos.find_one({"evento_id": evento_id})
        if not evento or evento.get("status") != "aguardando":
            await ctx.send("❌ Este evento não está disponível para iniciar uma luta.")
            return
        if not self.jogador_autorizado(ctx.author.id, evento):
            await ctx.send("❌ Você não pertence a este assentamento.")
            return
        resultado = self.eventos.update_one({"evento_id": evento_id, "status": "aguardando", "hostil": True}, {"$set": {"status": "combate", "combatente_id": str(ctx.author.id), "combate_iniciado_em": self.agora()}})
        await ctx.send(f"⚔️ {ctx.author.mention} iniciou a luta contra o evento `{evento_id}`." if resultado.modified_count else "❌ Não foi possível iniciar a luta.")

    @commands.command(name="evento_resolver")
    @commands.guild_only()
    async def evento_resolver(self, ctx, evento_id: str, resultado: str):
        evento = self.eventos.find_one({"evento_id": evento_id})
        if not evento:
            await ctx.send("❌ Evento não encontrado.")
            return
        if str(ctx.author.id) != str(evento.get("owner_id")):
            await ctx.send("❌ Apenas o dono do assentamento pode encerrar manualmente este evento.")
            return
        resultado = resultado.lower().strip()
        if resultado not in {"vitoria", "derrota"}:
            await ctx.send("❌ Use `vitoria` ou `derrota`.")
            return
        self.eventos.update_one({"_id": evento["_id"]}, {"$set": {"status": "resolvido" if resultado == "vitoria" else "fracassado", "resultado": resultado, "resolvido_em": self.agora()}})
        await ctx.send(f"{'🏆 Evento resolvido.' if resultado == 'vitoria' else '💀 Evento encerrado como derrota.'}")

    async def executar_ciclo(self):
        contagem = {"gerado": 0, "bloqueado": 0, "aguardando": 0, "nenhum": 0}
        for assentamento in self.assentamentos.find({"status": "ativo"}):
            try:
                resultado = await self.processar_assentamento(assentamento)
                contagem[resultado] = contagem.get(resultado, 0) + 1
            except Exception as erro:
                print(f"[EVENTOS][ERRO] {assentamento.get('assentamento_id')}: {erro}")
        print(f"🏕️ Ciclo de eventos: {contagem['gerado']} novos | {contagem['bloqueado']} aceitos/em combate | {contagem['aguardando']} aguardando decisão.")

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
