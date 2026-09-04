import asyncio
import random
from datetime import datetime, timezone
from uuid import uuid4

import discord
from discord.ext import commands

from database.python.mongodb import db

INTERVALO_SEGUNDOS = 60
CHANCE_EVENTO_POR_TERRITORIO = 0.35


class EventosAssentamentos(commands.Cog):
    """Gera acontecimentos autônomos nos canais territoriais dos assentamentos."""

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
                "cor": discord.Color.green(),
                "hostil": False,
                "dados": {"quantidade": quantidade},
            }
        if tipo == "bandidos":
            quantidade = random.randint(2, 8 + int(assentamento.get("nivel", 1)) // 10)
            return {
                "titulo": "⚔️ Bandidos avistados",
                "descricao": f"Um grupo de aproximadamente **{quantidade} bandidos** foi avistado próximo ao território de **{nome}**.",
                "cor": discord.Color.red(),
                "hostil": True,
                "dados": {"quantidade": quantidade},
            }
        if tipo == "monstro":
            nivel = int(assentamento.get("nivel", 1))
            ameaca = random.choice(["baixa", "moderada", "alta"] if nivel >= 30 else ["baixa", "moderada"])
            return {
                "titulo": "👹 Criatura hostil detectada",
                "descricao": f"Uma criatura de ameaça **{ameaca}** entrou ou se aproximou do território de **{nome}**.",
                "cor": discord.Color.dark_red(),
                "hostil": True,
                "dados": {"ameaca": ameaca},
            }
        if tipo == "mercador":
            return {
                "titulo": "🛒 Mercador itinerante",
                "descricao": f"Um mercador itinerante chegou ao território de **{nome}** oferecendo mercadorias e procurando oportunidades de comércio.",
                "cor": discord.Color.gold(),
                "hostil": False,
                "dados": {},
            }
        if tipo == "viajantes":
            return {
                "titulo": "🚶 Viajantes no território",
                "descricao": f"Viajantes atravessam o território de **{nome}**. Eles podem trazer notícias, oportunidades ou problemas.",
                "cor": discord.Color.blue(),
                "hostil": False,
                "dados": {},
            }
        if tipo == "recurso":
            recurso = random.choice(["madeira", "pedra", "água", "minério", "ervas"])
            return {
                "titulo": "🌿 Recurso descoberto",
                "descricao": f"Habitantes de **{nome}** encontraram uma possível fonte de **{recurso}** dentro ou perto do território.",
                "cor": discord.Color.teal(),
                "hostil": False,
                "dados": {"recurso": recurso},
            }
        if tipo == "caravana":
            return {
                "titulo": "🐎 Caravana chegou",
                "descricao": f"Uma caravana comercial alcançou o território de **{nome}**, trazendo pessoas, mercadorias e possíveis contatos comerciais.",
                "cor": discord.Color.orange(),
                "hostil": False,
                "dados": {},
            }
        return {
            "titulo": "⚠️ Ameaça territorial",
            "descricao": f"Uma situação incomum e potencialmente perigosa foi identificada nas proximidades de **{nome}**.",
            "cor": discord.Color.dark_orange(),
            "hostil": True,
            "dados": {},
        }

    async def processar_assentamento(self, assentamento):
        territorios = list(assentamento.get("territorios", []))
        if not territorios:
            return 0

        gerados = 0
        for canal_id in territorios:
            if random.random() > CHANCE_EVENTO_POR_TERRITORIO:
                continue

            canal = self.bot.get_channel(int(canal_id))
            if canal is None or not hasattr(canal, "send"):
                continue

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

            embed = discord.Embed(
                title=evento["titulo"],
                description=evento["descricao"],
                color=evento["cor"],
                timestamp=agora,
            )
            embed.add_field(name="🏕️ Assentamento", value=assentamento.get("nome", "Desconhecido"), inline=True)
            embed.add_field(name="🆔 Evento", value=f"`{evento_id}`", inline=True)
            embed.add_field(name="📌 Situação", value="⚔️ Ameaça ativa" if evento["hostil"] else "ℹ️ Acontecimento", inline=True)
            embed.set_footer(text="O mundo continua mesmo quando ninguém responde ao evento.")
            try:
                await canal.send(embed=embed)
                gerados += 1
            except (discord.Forbidden, discord.HTTPException) as erro:
                print(f"[EVENTOS][ERRO] Canal {canal_id}: {erro}")

        return gerados

    async def executar_ciclo(self):
        total = 0
        for assentamento in self.assentamentos.find({"status": "ativo"}):
            try:
                total += await self.processar_assentamento(assentamento)
            except Exception as erro:
                print(f"[EVENTOS][ERRO] Assentamento {assentamento.get('assentamento_id')}: {erro}")
        print(f"🏕️ Ciclo de eventos de assentamentos: {total} eventos gerados.")

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
