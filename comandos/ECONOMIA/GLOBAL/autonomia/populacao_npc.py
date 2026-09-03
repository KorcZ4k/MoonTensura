from datetime import datetime, timezone


class MotorPopulacaoNPC:
    """Etapa 5: população NPC, empregos, salários, desemprego e consumo."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.populacoes = db["Economia_Populacoes"]
        self.empresas = db["Economia_Empresas"]
        self.mercados = db["Mercados"]
        self.acontecimentos = db["Economia_Acontecimentos"]

    @staticmethod
    def _numero(valor):
        try:
            return max(0.0, float(valor or 0))
        except (TypeError, ValueError):
            return 0.0

    def _registrar(self, guild_id, titulo, descricao, dados, prioridade="normal"):
        self.acontecimentos.insert_one({
            "guild_id": str(guild_id),
            "tipo": "empresas",
            "titulo": titulo,
            "descricao": descricao,
            "dados": dados,
            "prioridade": prioridade,
            "criado_em": datetime.now(timezone.utc),
            "publicado": False,
        })

    def _empregos_disponiveis(self, guild_id):
        vagas = 0
        for empresa in self.empresas.find({"guild_id": str(guild_id), "status": "ativa"}):
            funcionarios = len(empresa.get("funcionarios") or [])
            capacidade = int(self._numero(empresa.get("capacidade_funcionarios")) or max(1, funcionarios + 5))
            vagas += max(0, capacidade - funcionarios)
        return vagas

    def processar_populacao(self, populacao):
        guild_id = str(populacao.get("guild_id"))
        total = int(self._numero(populacao.get("total") or populacao.get("populacao_total")))
        if total <= 0:
            return {"processada": False, "motivo": "sem_populacao"}

        trabalhadores = int(self._numero(populacao.get("trabalhadores")))
        desempregados = int(self._numero(populacao.get("desempregados")))
        if trabalhadores + desempregados == 0:
            trabalhadores = int(total * 0.55)
            desempregados = max(0, int(total * 0.08))

        vagas = self._empregos_disponiveis(guild_id)
        novas_contratacoes = min(desempregados, vagas, max(0, int(total * 0.03)))
        trabalhadores += novas_contratacoes
        desempregados = max(0, desempregados - novas_contratacoes)

        renda_media = self._numero(populacao.get("renda_media_bronze")) or 75.0
        massa_salarial = trabalhadores * renda_media
        consumo = massa_salarial * 0.72
        poupanca = massa_salarial - consumo
        agora = datetime.now(timezone.utc)

        # Distribui uma parcela da demanda pelos mercados da guilda.
        mercados = list(self.mercados.find({"guild_id": guild_id}))
        por_mercado = consumo / len(mercados) if mercados else 0
        for mercado in mercados:
            self.mercados.update_one(
                {"_id": mercado["_id"]},
                {"$inc": {"demanda_consumidor_bronze": por_mercado}, "$set": {"atualizado_em": agora}},
            )

        taxa_desemprego = desempregados / max(1, trabalhadores + desempregados)
        campos = {
            "trabalhadores": trabalhadores,
            "desempregados": desempregados,
            "vagas_economicas": vagas,
            "taxa_desemprego": taxa_desemprego,
            "massa_salarial_bronze": massa_salarial,
            "consumo_estimado_bronze": consumo,
            "poupanca_estimada_bronze": poupanca,
            "ultimo_ciclo_economico": agora,
        }
        self.populacoes.update_one({"_id": populacao["_id"]}, {"$set": campos})

        if novas_contratacoes > 0:
            self._registrar(
                guild_id,
                "🏢 Novas contratações na economia",
                f"{novas_contratacoes} NPCs encontraram trabalho durante o ciclo econômico.",
                {"contratacoes": novas_contratacoes, "taxa_desemprego": taxa_desemprego},
            )

        return {
            "processada": True,
            "populacao": total,
            "trabalhadores": trabalhadores,
            "desempregados": desempregados,
            "novas_contratacoes": novas_contratacoes,
            "taxa_desemprego": taxa_desemprego,
            "consumo_estimado_bronze": consumo,
        }

    def executar_ciclo(self):
        resultados = [self.processar_populacao(p) for p in self.populacoes.find({})]
        processadas = [r for r in resultados if r.get("processada")]
        return {
            "populacoes_processadas": len(processadas),
            "contratacoes": sum(int(r.get("novas_contratacoes", 0)) for r in processadas),
            "consumo_estimado_bronze": sum(self._numero(r.get("consumo_estimado_bronze")) for r in processadas),
            "resultados": resultados,
        }
