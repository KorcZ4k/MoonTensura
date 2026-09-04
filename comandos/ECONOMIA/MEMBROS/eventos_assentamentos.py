import asyncio
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import discord
from discord.ext import commands

from database.python.mongodb import db

CONFIG_PATH = Path(__file__).resolve().parents[3] / "database" / "json" / "ev_assent.json"


class EventosAssentamentos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.assentamentos = db["Economia_Assentamentos"]
        self.eventos = db["Economia_Eventos_Assentamentos"]
        self._ativo = False
        self._tarefa = None
        self.config = self.carregar_config()

    @staticmethod
    def agora():
        return datetime.now(timezone.utc)

    def carregar_config(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as arquivo:
                return json.load(arquivo)
        except Exception as erro:
            print(f"[EVENTOS] Erro ao carregar ev_assent.json: {erro}")
            return {"configuracao": {}, "eventos": {}, "assentamento": {}}

    @property
    def intervalo(self):
        return int(self.config.get("configuracao", {}).get("intervalo_eventos_segundos", 60))

    @property
    def chance(self):
        return float(self.config.get("configuracao", {}).get("chance_evento", 0.35))

    def garantir_assentamento(self, assentamento):
        cfg = self.config.get("assentamento", {})
        recursos = dict(assentamento.get("recursos", {}))
        for recurso in cfg.get("recursos_iniciais", []):
            recursos.setdefault(recurso, 0)

        dados = {
            "recursos": recursos,
            "estoque_armas": assentamento.get("estoque_armas", {}),
            "edificios_construidos": assentamento.get("edificios_construidos", {}),
            "edificios_em_construcao": assentamento.get("edificios_em_construcao", {}),
            "xp_eventos_multiplicador": max(0.0, float(assentamento.get("xp_eventos_multiplicador", cfg.get("xp_eventos_multiplicador_inicial", 1.0)))),
            "xp_eventos_perdido_percentual": max(0.0, float(assentamento.get("xp_eventos_perdido_percentual", 0.0))),
        }
        self.assentamentos.update_one({"_id": assentamento["_id"]}, {"$set": dados})
        assentamento.update(dados)
        return assentamento

    @staticmethod
    def fibonacci(nivel):
        a, b = 1, 1
        for _ in range(max(0, nivel - 2)):
            a, b = b, a + b
        return a if nivel <= 1 else b

    def gerar_bandido(self, nivel):
        ficha = self.config.get("eventos", {}).get("bandidos", {}).get("ficha", {})
        valor = round(
            float(ficha.get("atributos_nivel_1", 100))
            * (float(ficha.get("multiplicador_por_nivel", 1.75)) ** max(0, nivel - 1))
        )
        atributos = {atributo.lower().replace("ç", "c"): valor for atributo in ficha.get("atributos", [])}
        magias = []
        if ficha.get("magias") and random.random() < 0.35:
            magias = [{"nome": "Magia de Bandido", "nivel": nivel}]
        return {
            "id": f"band-{uuid4().hex[:8]}",
            "nivel": nivel,
            "atributos": atributos,
            "habilidades": [],
            "magias": magias,
        }

    def escolher_evento(self):
        eventos = self.config.get("eventos", {})
        opcoes = [
            (nome, dados.get("peso", 0))
            for nome, dados in eventos.items()
            if dados.get("geracao_automatica", True) and dados.get("peso", 0) > 0
        ]
        if not opcoes:
            return None
        return random.choices([x[0] for x in opcoes], weights=[x[1] for x in opcoes], k=1)[0]

    def criar_dados_evento(self, tipo, assentamento):
        nome = assentamento.get("nome", "Assentamento")
        nivel = int(assentamento.get("nivel", 1))
        recursos = self.config.get("assentamento", {}).get("recursos_iniciais", [])

        if tipo == "refugiados":
            quantidade = self.fibonacci(nivel)
            return "🏕️ Refugiados chegaram", f"**{quantidade} refugiado(s)** chegaram a **{nome}**.", discord.Color.green(), False, {"quantidade": quantidade}
        if tipo == "bandidos":
            quantidade = max(1, min(10, nivel))
            fichas = [self.gerar_bandido(max(1, nivel)) for _ in range(quantidade)]
            return "⚔️ Bandidos avistados", f"**{quantidade} bandido(s)** ameaçam o território de **{nome}**.", discord.Color.red(), True, {"quantidade": quantidade, "nivel_inimigo": max(1, nivel), "fichas": fichas}
        if tipo == "monstro":
            nivel_monstro = 1 if nivel <= 2 else nivel - 1
            return "👹 Monstro hostil", f"Uma criatura hostil de nível **{nivel_monstro}** aproxima-se de **{nome}**.", discord.Color.dark_red(), True, {"nivel_inimigo": nivel_monstro}
        if tipo == "mercador":
            variacoes = self.config.get("eventos", {}).get(tipo, {}).get("preco", {}).get("variacoes_percentuais", [-10, 10])
            variacao = random.choice(variacoes)
            texto = "menores" if variacao < 0 else "maiores"
            return "🛒 Mercador itinerante", f"Um mercador chegou. Seus preços estão **{abs(variacao)}% {texto}** que o mercado.", discord.Color.gold(), False, {"variacao_preco": variacao}
        if tipo == "viajantes":
            resultados = self.config.get("eventos", {}).get(tipo, {}).get("resultados", ["virar_populacao"])
            return "🚶 Viajantes", f"Viajantes chegaram a **{nome}**.", discord.Color.blue(), False, {"resultado": random.choice(resultados)}
        if tipo == "descoberta_recurso":
            recurso = random.choice(recursos) if recursos else "recurso"
            return "🌿 Descoberta de recurso", f"Uma fonte de **{recurso}** foi encontrada.", discord.Color.teal(), False, {"recurso": recurso, "utilizavel": random.choice([True, False])}
        return "🐎 Caravana", f"Uma caravana chegou a **{nome}**.", discord.Color.orange(), False, {}

    def autorizado(self, user_id, evento):
        if str(user_id) == str(evento.get("owner_id")):
            return True
        assentamento = self.assentamentos.find_one({"assentamento_id": evento.get("assentamento_id")}) or {}
        return str(user_id) in [str(x) for x in assentamento.get("membros", [])]

    def pendente(self, assentamento_id):
        # Apenas um combate ativo bloqueia novos eventos. Eventos aceitos e já
        # processados nunca devem permanecer bloqueando o assentamento.
        return self.eventos.find_one({
            "assentamento_id": str(assentamento_id),
            "status": "combate",
        })

    def aguardando(self, assentamento_id):
        return self.eventos.find_one({
            "assentamento_id": str(assentamento_id),
            "status": "aguardando",
        }, sort=[("criado_em", -1)])

    async def aplicar_pacifico(self, evento):
        assentamento = self.assentamentos.find_one({"assentamento_id": evento["assentamento_id"]})
        if not assentamento:
            return

        dados = evento.get("dados", {})
        alteracoes = {}
        if evento["tipo"] == "refugiados":
            alteracoes["populacao"] = int(assentamento.get("populacao", 0)) + int(dados.get("quantidade", 0))
        elif evento["tipo"] == "viajantes":
            resultado = dados.get("resultado")
            if resultado == "virar_populacao":
                alteracoes["populacao"] = int(assentamento.get("populacao", 0)) + 1
            elif resultado == "roubar_10_porcento_hunos_bronze":
                saldo = max(0, int(assentamento.get("saldo_bronze", 0)))
                alteracoes["saldo_bronze"] = max(0, saldo - math.floor(saldo * 0.10))
            elif resultado == "roubar_um_tipo_de_recurso":
                recursos = dict(assentamento.get("recursos", {}))
                disponiveis = [recurso for recurso, quantidade in recursos.items() if quantidade > 0]
                if disponiveis:
                    recursos[random.choice(disponiveis)] = 0
                    alteracoes["recursos"] = recursos
        elif evento["tipo"] == "descoberta_recurso":
            alteracoes["ultimo_recurso_descoberto"] = dados["recurso"] if dados.get("utilizavel") else None

        xp = max(1, int(evento.get("xp_assentamento", 1)))
        multiplicador = max(0.0, float(evento.get("xp_multiplicador", 1.0)))
        alteracoes["xp"] = int(assentamento.get("xp", 0)) + math.floor(xp * multiplicador)

        if alteracoes:
            alteracoes["atualizado_em"] = self.agora()
            self.assentamentos.update_one({"_id": assentamento["_id"]}, {"$set": alteracoes})

    async def responder(self, interaction, evento_id, acao):
        evento = self.eventos.find_one({"evento_id": evento_id, "status": "aguardando"})
        if not evento:
            await interaction.response.send_message("❌ Este evento não está mais disponível.", ephemeral=True)
            return
        if not self.autorizado(interaction.user.id, evento):
            await interaction.response.send_message("❌ Você não pertence a este assentamento.", ephemeral=True)
            return

        if acao == "recusar":
            status = "recusado"
        elif acao == "lutar" and evento.get("hostil"):
            status = "combate"
        elif acao == "aceitar":
            status = "aceito"
        else:
            await interaction.response.send_message("❌ Ação inválida.", ephemeral=True)
            return

        agora = self.agora()
        campos = {
            "status": status,
            "respondido_por": str(interaction.user.id),
            "respondido_em": agora,
        }
        if status == "combate":
            campos.update({
                "combatente_id": str(interaction.user.id),
                "combate_iniciado_em": agora,
            })

        resultado = self.eventos.update_one(
            {"_id": evento["_id"], "status": "aguardando"},
            {"$set": campos},
        )
        if not resultado.modified_count:
            await interaction.response.send_message("❌ Este evento já mudou de estado.", ephemeral=True)
            return

        if status == "aceito":
            if not evento.get("hostil"):
                evento["status"] = "aceito"
                await self.aplicar_pacifico(evento)
                # O efeito já foi aplicado: encerra imediatamente para não bloquear.
                self.eventos.update_one(
                    {"_id": evento["_id"]},
                    {"$set": {"status": "concluido", "concluido_em": self.agora()}},
                )
                texto = "✅ Evento aceito e concluído. O assentamento já pode receber novos eventos."
            else:
                # Aceitar uma ameaça sem iniciar combate não pode travar o sistema.
                self.eventos.update_one(
                    {"_id": evento["_id"]},
                    {"$set": {"status": "concluido", "concluido_em": self.agora(), "resolucao": "ameaca_aceita_sem_combate"}},
                )
                texto = "✅ Evento aceito e encerrado. O assentamento não ficou bloqueado."
        elif status == "recusado":
            texto = "❌ Evento recusado e encerrado. Novos eventos podem aparecer normalmente."
        else:
            texto = "⚔️ Combate iniciado. Enquanto a luta estiver ativa, novos eventos ficarão bloqueados."

        await interaction.response.send_message(texto)

    def view_evento(self, evento_id, hostil):
        view = discord.ui.View(timeout=None)
        for texto, estilo, acao in [
            ("✅ Aceitar", discord.ButtonStyle.success, "aceitar"),
            ("❌ Recusar", discord.ButtonStyle.secondary, "recusar"),
        ]:
            botao = discord.ui.Button(label=texto, style=estilo, custom_id=f"ass_evento:{acao}:{evento_id}")

            async def callback(interaction, e=evento_id, a=acao):
                await self.responder(interaction, e, a)

            botao.callback = callback
            view.add_item(botao)

        if hostil:
            botao = discord.ui.Button(label="⚔️ Lutar", style=discord.ButtonStyle.danger, custom_id=f"ass_evento:lutar:{evento_id}")

            async def lutar(interaction, e=evento_id):
                await self.responder(interaction, e, "lutar")

            botao.callback = lutar
            view.add_item(botao)
        return view

    async def expirar(self, assentamento, evento):
        perda = float(self.config.get("configuracao", {}).get("xp_perdido_por_evento_ignorado_percentual", 1)) / 100
        atual = max(0.0, float(assentamento.get("xp_eventos_multiplicador", 1.0)))
        novo = max(0.0, atual * (1 - perda))
        perdido = min(100.0, float(assentamento.get("xp_eventos_perdido_percentual", 0)) + perda * 100)
        agora = self.agora()
        self.eventos.update_one({"_id": evento["_id"]}, {"$set": {"status": "ignorado", "ignorado_em": agora}})
        self.assentamentos.update_one({"_id": assentamento["_id"]}, {"$set": {
            "xp_eventos_multiplicador": novo,
            "xp_eventos_perdido_percentual": perdido,
            "atualizado_em": agora,
        }})

    async def processar(self, assentamento):
        assentamento = self.garantir_assentamento(assentamento)

        if self.pendente(assentamento["assentamento_id"]):
            return "bloqueado"

        evento = self.aguardando(assentamento["assentamento_id"])
        if evento:
            if (self.agora() - evento["criado_em"]).total_seconds() < self.intervalo:
                return "aguardando"
            await self.expirar(assentamento, evento)

        territorios = assentamento.get("territorios", [])
        if not territorios or random.random() > self.chance:
            return "nenhum"

        canal = self.bot.get_channel(int(random.choice(territorios)))
        if canal is None or not hasattr(canal, "send"):
            return "nenhum"

        tipo = self.escolher_evento()
        if not tipo:
            return "nenhum"

        titulo, descricao, cor, hostil, dados = self.criar_dados_evento(tipo, assentamento)
        evento_id = f"evt-ass-{uuid4().hex[:12]}"
        agora = self.agora()
        documento = {
            "evento_id": evento_id,
            "tipo": tipo,
            "guild_id": str(assentamento.get("guild_id", "")),
            "owner_id": str(assentamento.get("owner_id", "")),
            "assentamento_id": assentamento["assentamento_id"],
            "canal_id": str(canal.id),
            "status": "aguardando",
            "hostil": hostil,
            "dados": dados,
            "xp_multiplicador": max(0.0, float(assentamento.get("xp_eventos_multiplicador", 1.0))),
            "xp_assentamento": max(1, int(assentamento.get("nivel", 1))),
            "criado_em": agora,
        }
        self.eventos.insert_one(documento)

        embed = discord.Embed(title=titulo, description=descricao, color=cor, timestamp=agora)
        embed.add_field(name="🏕️ Assentamento", value=assentamento.get("nome", "Desconhecido"), inline=True)
        embed.add_field(name="🆔 Evento", value=f"`{evento_id}`", inline=True)
        embed.add_field(name="⏱️ Decisão", value=f"Você tem {self.intervalo} segundos para decidir.", inline=False)
        if hostil:
            embed.add_field(name="⚔️ Combate", value="Clique em **Lutar** para iniciar o confronto.", inline=False)

        await canal.send(embed=embed, view=self.view_evento(evento_id, hostil))
        return "gerado"

    async def executar_ciclo(self):
        contagem = {"gerado": 0, "bloqueado": 0, "aguardando": 0, "nenhum": 0}
        for assentamento in self.assentamentos.find({"status": "ativo"}):
            try:
                resultado = await self.processar(assentamento)
                contagem[resultado] = contagem.get(resultado, 0) + 1
            except Exception as erro:
                print(f"[EVENTOS][ERRO] {assentamento.get('assentamento_id')}: {erro}")
        print(f"🏕️ Ciclo de eventos: {contagem['gerado']} gerados | {contagem['bloqueado']} bloqueados | {contagem['aguardando']} aguardando.")

    async def loop(self):
        while self._ativo:
            await asyncio.sleep(self.intervalo)
            self.config = self.carregar_config()
            await self.executar_ciclo()

    @commands.Cog.listener()
    async def on_ready(self):
        if self._ativo:
            return
        self._ativo = True
        self._tarefa = asyncio.create_task(self.loop())
        print(f"🏕️ Eventos de assentamentos iniciados: intervalo de {self.intervalo}s.")

    def cog_unload(self):
        self._ativo = False
        if self._tarefa:
            self._tarefa.cancel()


async def setup(bot):
    await bot.add_cog(EventosAssentamentos(bot))
