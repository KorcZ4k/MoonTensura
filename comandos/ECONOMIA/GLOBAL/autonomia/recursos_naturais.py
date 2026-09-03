from datetime import datetime, timezone


class MotorRecursosNaturais:
    """Etapa 11: recursos finitos, extração, regeneração e matéria-prima."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.recursos = db["Economia_RecursosNaturais"]
        self.empresas = db["Economia_Empresas"]
        self.acontecimentos = db["Economia_Acontecimentos"]

    @staticmethod
    def _numero(valor, padrao=0.0):
        try:
            return max(0.0, float(valor if valor is not None else padrao))
        except (TypeError, ValueError):
            return float(padrao)

    def _registrar(self, guild_id, titulo, descricao, dados, prioridade="normal"):
        self.acontecimentos.insert_one({
            "guild_id": str(guild_id), "tipo": "crises_financeiras",
            "titulo": titulo, "descricao": descricao, "dados": dados,
            "prioridade": prioridade, "criado_em": datetime.now(timezone.utc),
            "publicado": False,
        })

    def processar_recurso(self, recurso):
        estoque = self._numero(recurso.get("estoque_atual"))
        capacidade = max(estoque, self._numero(recurso.get("capacidade_maxima"), estoque))
        regeneracao = self._numero(recurso.get("regeneracao_por_ciclo"))
        taxa_extracao = self._numero(recurso.get("extracao_por_ciclo"))
        tipo = recurso.get("tipo", "materia_prima")
        renovavel = bool(recurso.get("renovavel", False))

        # Recursos não surgem do nada: apenas os renováveis regeneram naturalmente.
        disponivel = min(capacidade, estoque + regeneracao) if renovavel else estoque
        extracao = min(disponivel, taxa_extracao)
        novo_estoque = max(0.0, disponivel - extracao)
        esgotado = novo_estoque <= 0.0
        percentual = novo_estoque / max(1.0, capacidade)

        self.recursos.update_one({"_id": recurso["_id"]}, {"$set": {"estoque_atual": novo_estoque, "ultima_extracao": extracao, "percentual_disponivel": percentual, "atualizado_em": datetime.now(timezone.utc)}})

        if esgotado and not recurso.get("alerta_esgotamento"):
            self.recursos.update_one({"_id": recurso["_id"]}, {"$set": {"alerta_esgotamento": True}})
            self._registrar(recurso.get("guild_id"), "🚨 Recurso esgotado", "Um recurso natural foi completamente esgotado, interrompendo sua extração local.", {"recurso_id": str(recurso["_id"]), "tipo": tipo, "territorio": recurso.get("territorio")}, "alta")
        elif percentual <= 0.15 and not recurso.get("alerta_escassez"):
            self.recursos.update_one({"_id": recurso["_id"]}, {"$set": {"alerta_escassez": True}})
            self._registrar(recurso.get("guild_id"), "⚠️ Escassez de recurso", "A quantidade disponível de um recurso natural atingiu um nível crítico.", {"recurso_id": str(recurso["_id"]), "tipo": tipo, "percentual": percentual}, "alta")

        return {"extraido": extracao, "estoque": novo_estoque, "esgotado": esgotado}

    def executar_ciclo(self):
        resultados = [self.processar_recurso(r) for r in self.recursos.find({})]
        return {
            "recursos_processados": len(resultados),
            "unidades_extraidas": sum(r["extraido"] for r in resultados),
            "recursos_esgotados": sum(1 for r in resultados if r["esgotado"]),
            "recursos_em_escassez": sum(1 for r in resultados if r["estoque"] > 0 and r["estoque"] <= 1),
        }
