import asyncio
import random
from types import SimpleNamespace

from discord.ext import commands

from database.python.mongodb import db
from database.python.luta import criar_participante_jogador, obter_vencedores
from comandos.ECONOMIA.MEMBROS.monstros_assentamentos import gerar_monstro_hostil


class CombateEventosAssentamentos(commands.Cog):
    """Liga bandidos e monstros dos assentamentos ao sistema principal de luta."""

    def __init__(self, bot):
        self.bot = bot
        self.eventos = db["Economia_Eventos_Assentamentos"]
        self.assentamentos = db["Economia_Assentamentos"]
        self._tarefa = None
        self._iniciado = False
        self._finalizar_original = None

    @staticmethod
    def _agora():
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)

    @commands.Cog.listener()
    async def on_ready(self):
        if self._iniciado:
            return
        self._iniciado = True
        await self._instalar_integracao_luta()
        self._tarefa = asyncio.create_task(self._loop())

    async def _instalar_integracao_luta(self):
        for _ in range(20):
            luta = self.bot.get_cog("Luta")
            if luta:
                break
            await asyncio.sleep(1)
        else:
            print("[ASSENTAMENTO][COMBATE] Cog Luta não encontrado.")
            return
        if getattr(luta, "_eventos_assentamentos_integrado", False):
            return

        self._finalizar_original = luta._finalizar
        integrador = self

        async def finalizar_integrado(ctx, *args, **kwargs):
            combate = luta.combates.get(ctx.channel.id)
            metadados = dict(combate.get("evento_assentamento", {})) if combate else {}
            resultado = obter_vencedores(combate) if combate else None
            await integrador._finalizar_original(ctx, *args, **kwargs)
            if metadados:
                await integrador._concluir_evento(metadados, resultado)

        luta._finalizar = finalizar_integrado
        luta._eventos_assentamentos_integrado = True
        print("[ASSENTAMENTO][COMBATE] Integração com o sistema de luta instalada.")

    def _criar_inimigo_bandido(self, ficha, evento_id):
        atributos = ficha.get("atributos", {})
        nivel = max(1, int(ficha.get("nivel", 1)))
        vida = max(100, int(atributos.get("vitalidade", atributos.get("forca", ficha.get("vida", 100)))))
        return {
            "id": str(ficha.get("id", f"bandido-{evento_id}")),
            "tipo": "monstro",
            "monstro_id": "bandido",
            "nome": f"Bandido Nível {nivel}",
            "emoji": "🗡️",
            "vida": vida,
            "vida_maxima": vida,
            "mana": int(atributos.get("magia", 0)),
            "forca": int(atributos.get("forca", 100)),
            "defesa": int(atributos.get("defesa", 100)),
            "velocidade": int(atributos.get("velocidade", 100)),
            "destreza": int(atributos.get("destreza", 100)),
            "magia": int(atributos.get("magia", 100)),
            "nivel": nivel,
            "habilidades": [],
            "magias": ficha.get("magias", []),
            "xp_recompensa": max(1, nivel * 100),
            "hunos_recompensa": max(1, nivel * 50),
        }

    def _criar_inimigo_monstro(self, ficha, evento_id):
        atributos = ficha.get("atributos", {})
        nivel = max(1, int(ficha.get("nivel", 1)))
        vida = max(1, int(ficha.get("vida_maxima", ficha.get("vida", 100))))
        return {
            "id": str(ficha.get("id", f"monstro-{evento_id}")),
            "tipo": "monstro",
            "monstro_id": str(ficha.get("monstro_base", "monstro_hostil")),
            "nome": str(ficha.get("nome", ficha.get("raca", "Monstro Hostil"))),
            "emoji": str(ficha.get("emoji", "👹")),
            "raca": ficha.get("raca"),
            "vida": vida,
            "vida_maxima": vida,
            "mana": int(atributos.get("magia", 0)),
            "forca": int(atributos.get("forca", ficha.get("dano", 10))),
            "defesa": int(atributos.get("defesa", 10)),
            "velocidade": int(atributos.get("velocidade", 10)),
            "destreza": int(atributos.get("destreza", 10)),
            "magia": int(atributos.get("magia", 0)),
            "nivel": nivel,
            "habilidades": list(ficha.get("habilidades", [])),
            "magias": list(ficha.get("magias", [])),
            "xp_recompensa": int(ficha.get("recompensas", {}).get("xp_jogador", nivel * 100)),
            "hunos_recompensa": int(ficha.get("recompensas", {}).get("hunos", nivel * 50)),
        }

    def _obter_ou_gerar_monstro(self, evento):
        dados = dict(evento.get("dados", {}))
        ficha = dados.get("ficha")
        if ficha:
            return ficha

        assentamento = self.assentamentos.find_one({"assentamento_id": evento.get("assentamento_id")})
        nivel_assentamento = int((assentamento or {}).get("nivel", 1))
        ficha = gerar_monstro_hostil(nivel_assentamento)
        if not ficha:
            return None

        dados["ficha"] = ficha
        dados["nivel_inimigo"] = int(ficha.get("nivel", 1))
        self.eventos.update_one(
            {"_id": evento["_id"]},
            {"$set": {"dados": dados, "ficha_gerada_em": self._agora()}},
        )
        evento["dados"] = dados
        return ficha

    async def _iniciar_evento(self, evento):
        canal_id = int(evento.get("canal_id", 0) or 0)
        canal = self.bot.get_channel(canal_id)
        luta = self.bot.get_cog("Luta")
        if canal is None or luta is None or luta._combate_ativo(canal_id):
            return False

        guild_id = str(evento.get("guild_id", ""))
        jogador_id = str(evento.get("combatente_id", evento.get("respondido_por", "")))
        jogador = criar_participante_jogador(jogador_id, guild_id)
        if not jogador:
            self.eventos.update_one({"_id": evento["_id"]}, {"$set": {"status": "erro_combate", "erro": "Jogador sem personagem"}})
            return False

        membro = canal.guild.get_member(int(jogador_id)) if canal.guild and jogador_id.isdigit() else None
        jogador["nome"] = jogador.get("nome") or (membro.display_name if membro else jogador_id)

        tipo = evento.get("tipo")
        if tipo == "bandidos":
            fichas = evento.get("dados", {}).get("fichas", [])
            if not fichas:
                return False
            inimigo = self._criar_inimigo_bandido(fichas[0], evento.get("evento_id", "evento"))
        elif tipo == "monstro":
            ficha = self._obter_ou_gerar_monstro(evento)
            if not ficha:
                self.eventos.update_one({"_id": evento["_id"]}, {"$set": {"status": "erro_combate", "erro": "Não foi possível gerar o monstro"}})
                return False
            inimigo = self._criar_inimigo_monstro(ficha, evento.get("evento_id", "evento"))
        else:
            return False

        participantes = [jogador, inimigo]
        participantes.sort(key=lambda p: p.get("velocidade", 0), reverse=True)
        luta.combates[canal_id] = {
            "participantes": participantes,
            "turno": 0,
            "numero_turno": 1,
            "fase": "ataque",
            "ativo": True,
            "pvp": False,
            "guild_id": guild_id,
            "ataque_pendente": None,
            "historico": [],
            "aguardando_finalizacao": False,
            "vencedor_id": None,
            "perdedor_id": None,
            "evento_assentamento": {
                "evento_id": evento["evento_id"],
                "assentamento_id": evento["assentamento_id"],
                "jogador_id": jogador_id,
                "tipo_inimigo": tipo,
                "nivel_inimigo": int(evento.get("dados", {}).get("nivel_inimigo", inimigo.get("nivel", 1))),
            },
        }
        luta._atualizar_situacao(jogador_id, guild_id, "ativo_combate")
        contexto = SimpleNamespace(channel=canal, send=canal.send)
        await luta._mostrar_inicio(contexto)
        return True

    def _arma_recompensa(self, nivel, tipo):
        if tipo == "monstro":
            armas = ["Presa Reforçada", "Garra Afiada", "Chifre de Combate", "Núcleo Cristalizado"]
        else:
            armas = ["Adaga de Ferro", "Espada Curta", "Machado de Guerra", "Lança de Ferro", "Espada Longa"]
        return {"nome": random.choice(armas), "nivel_origem": nivel, "quantidade": 1, "origem": tipo}

    async def _concluir_evento(self, meta, resultado):
        evento = self.eventos.find_one({"evento_id": meta.get("evento_id")})
        assentamento = self.assentamentos.find_one({"assentamento_id": meta.get("assentamento_id")})
        if not evento or not assentamento:
            return

        vitoria = bool(isinstance(resultado, dict) and resultado.get("tipo") == "vitoria" and resultado.get("lado") == "jogadores")
        nivel = max(1, int(meta.get("nivel_inimigo", 1)))
        tipo = str(meta.get("tipo_inimigo", evento.get("tipo", "bandido")))

        if not vitoria:
            self.eventos.update_one({"_id": evento["_id"]}, {"$set": {"status": "derrota", "concluido_em": self._agora()}})
            return

        multiplicador = max(0.0, float(evento.get("xp_multiplicador", 1.0)))
        ficha = evento.get("dados", {}).get("ficha", {}) if tipo == "monstro" else {}
        recompensas_ficha = ficha.get("recompensas", {})
        xp_jogador_base = int(recompensas_ficha.get("xp_jogador", nivel * 100))
        xp_assentamento_base = int(recompensas_ficha.get("xp_assentamento", nivel * 50))
        hunos = max(0, int(recompensas_ficha.get("hunos", nivel * 50)))
        xp_jogador = max(0, int(xp_jogador_base * multiplicador))
        xp_assentamento = max(0, int(xp_assentamento_base * multiplicador))
        arma = self._arma_recompensa(nivel, tipo)

        if xp_jogador:
            db["Jogadores"].update_one(
                {"ID": str(meta["jogador_id"]), "guild_id": str(evento.get("guild_id", ""))},
                {"$inc": {"XP": xp_jogador}},
            )
        if hunos:
            db["Hunos"].update_one(
                {"ID": str(meta["jogador_id"]), "guild_id": str(evento.get("guild_id", ""))},
                {"$inc": {"carteira": hunos}},
                upsert=True,
            )

        estoque = list(assentamento.get("estoque_armas", []))
        if isinstance(estoque, dict):
            estoque = list(estoque.values())
        estoque.append(arma)
        self.assentamentos.update_one(
            {"_id": assentamento["_id"]},
            {"$set": {"estoque_armas": estoque}, "$inc": {"xp": xp_assentamento}},
        )
        self.eventos.update_one(
            {"_id": evento["_id"]},
            {"$set": {
                "status": "vitoria",
                "concluido_em": self._agora(),
                "recompensas": {
                    "xp_jogador": xp_jogador,
                    "xp_assentamento": xp_assentamento,
                    "hunos": hunos,
                    "arma": arma,
                },
            }},
        )

    async def _loop(self):
        while self._iniciado:
            try:
                for evento in self.eventos.find({"status": "combate", "tipo": {"$in": ["bandidos", "monstro"]}}):
                    if evento.get("combate_conectado"):
                        continue
                    iniciado = await self._iniciar_evento(evento)
                    if iniciado:
                        self.eventos.update_one({"_id": evento["_id"]}, {"$set": {"combate_conectado": True}})
            except Exception as erro:
                print(f"[ASSENTAMENTO][COMBATE] Erro: {erro}")
            await asyncio.sleep(2)

    def cog_unload(self):
        self._iniciado = False
        if self._tarefa:
            self._tarefa.cancel()


async def setup(bot):
    await bot.add_cog(CombateEventosAssentamentos(bot))
