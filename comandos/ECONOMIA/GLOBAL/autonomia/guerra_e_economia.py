from datetime import datetime, timezone


class MotorGuerraEEconomia:
    """Etapa 12: impactos econômicos de guerras, cercos e destruição."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.conflitos = db["Economia_Conflitos"]
        self.rotas = db["Economia_Rotas"]
        self.empresas = db["Economia_Empresas"]
        self.recursos = db["Economia_RecursosNaturais"]
        self.acontecimentos = db["Economia_Acontecimentos"]

    @staticmethod
    def _numero(valor, padrao=0.0):
        try:
            return max(0.0, float(valor if valor is not None else padrao))
        except (TypeError, ValueError):
            return float(padrao)

    def _registrar(self, guild_id, titulo, descricao, dados, prioridade="alta"):
        self.acontecimentos.insert_one({
            "guild_id": str(guild_id), "tipo": "crises_financeiras",
            "titulo": titulo, "descricao": descricao, "dados": dados,
            "prioridade": prioridade, "criado_em": datetime.now(timezone.utc),
            "publicado": False,
        })

    def _territorios(self, conflito):
        valores = conflito.get("territorios") or []
        for campo in ("territorio", "atacante", "defensor", "origem", "destino"):
            valor = conflito.get(campo)
            if valor:
                valores.append(valor)
        return {str(v) for v in valores if v}

    def processar_conflito(self, conflito):
        if conflito.get("status", "ativo") not in {"ativo", "guerra", "cerco"}:
            return {"acao": "ignorado"}

        territorios = self._territorios(conflito)
        if not territorios:
            return {"acao": "ignorado", "motivo": "sem_territorio"}

        intensidade = min(1.0, self._numero(conflito.get("intensidade"), 0.5))
        destruicao = min(0.8, intensidade * 0.10)
        bloqueio = min(1.0, self._numero(conflito.get("bloqueio_comercial"), intensidade * 0.5))

        empresas_afetadas = 0
        rotas_interrompidas = 0
        recursos_perdidos = 0.0

        for empresa in self.empresas.find({"status": "ativa"}):
            territorio = str(empresa.get("territorio") or empresa.get("pais") or empresa.get("reino") or "")
            if territorio not in territorios:
                continue
            producao = self._numero(empresa.get("capacidade_producao"))
            nova_producao = producao * (1.0 - destruicao)
            self.empresas.update_one({"_id": empresa["_id"]}, {"$set": {"capacidade_producao": nova_producao, "impacto_guerra": True, "ultima_atualizacao_guerra": datetime.now(timezone.utc)}})
            empresas_afetadas += 1

        for rota in self.rotas.find({"status": {"$in": ["ativa", "pendente"]}}):
            origem = rota.get("territorio_origem") or {}
            destino = rota.get("territorio_destino") or {}
            locais = {str(origem.get(k)) for k in ("regiao", "reino", "pais") if origem.get(k)} | {str(destino.get(k)) for k in ("regiao", "reino", "pais") if destino.get(k)}
            if territorios & locais and bloqueio > 0:
                self.rotas.update_one({"_id": rota["_id"]}, {"$set": {"status": "interrompida", "motivo_interrupcao": "conflito", "impacto_guerra": bloqueio}})
                rotas_interrompidas += 1

        for recurso in self.recursos.find({}):
            territorio = str(recurso.get("territorio") or recurso.get("pais") or recurso.get("reino") or "")
            if territorio not in territorios:
                continue
            estoque = self._numero(recurso.get("estoque_atual"))
            perda = estoque * destruicao
            self.recursos.update_one({"_id": recurso["_id"]}, {"$inc": {"estoque_atual": -perda}, "$set": {"impacto_conflito": True}})
            recursos_perdidos += perda

        if not conflito.get("impacto_economico_registrado"):
            self.conflitos.update_one({"_id": conflito["_id"]}, {"$set": {"impacto_economico_registrado": True}})
            self._registrar(conflito.get("guild_id"), "⚔️ Impacto econômico da guerra", "O conflito começou a afetar empresas, recursos e rotas comerciais.", {"conflito_id": str(conflito["_id"]), "territorios": list(territorios), "empresas_afetadas": empresas_afetadas, "rotas_interrompidas": rotas_interrompidas})

        return {"acao": "processado", "empresas_afetadas": empresas_afetadas, "rotas_interrompidas": rotas_interrompidas, "recursos_perdidos": recursos_perdidos}

    def executar_ciclo(self):
        resultados = [self.processar_conflito(c) for c in self.conflitos.find({})]
        processados = [r for r in resultados if r.get("acao") == "processado"]
        return {"conflitos_processados": len(processados), "empresas_afetadas": sum(r["empresas_afetadas"] for r in processados), "rotas_interrompidas": sum(r["rotas_interrompidas"] for r in processados), "recursos_perdidos": sum(r["recursos_perdidos"] for r in processados)}
