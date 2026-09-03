from datetime import datetime, timezone


class MotorDiplomaciaEconomica:
    """Etapa 13: tratados, sanções, embargos e relações econômicas."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.acordos = db["Economia_Tratados"]
        self.sancoes = db["Economia_Sancoes"]
        self.relacoes = db["Economia_RelacoesDiplomaticas"]
        self.rotas = db["Economia_Rotas"]
        self.acontecimentos = db["Economia_Acontecimentos"]

    @staticmethod
    def _numero(valor, padrao=0.0):
        try:
            return max(0.0, float(valor if valor is not None else padrao))
        except (TypeError, ValueError):
            return float(padrao)

    def _registrar(self, guild_id, titulo, descricao, dados, prioridade="normal"):
        self.acontecimentos.insert_one({
            "guild_id": str(guild_id),
            "tipo": "tratados_empresariais",
            "titulo": titulo,
            "descricao": descricao,
            "dados": dados,
            "prioridade": prioridade,
            "criado_em": datetime.now(timezone.utc),
            "publicado": False,
        })

    @staticmethod
    def _territorios(documento):
        partes = documento.get("territorios") or documento.get("participantes") or []
        for campo in ("origem", "destino", "pais_a", "pais_b", "atacante", "alvo"):
            if documento.get(campo):
                partes.append(documento[campo])
        return {str(x) for x in partes if x}

    def _rotas_afetadas(self, territorios):
        afetadas = []
        for rota in self.rotas.find({"status": {"$ne": "encerrada"}}):
            origem = rota.get("territorio_origem") or {}
            destino = rota.get("territorio_destino") or {}
            locais = {
                str(v) for v in (
                    origem.get("pais"), origem.get("reino"), origem.get("regiao"),
                    destino.get("pais"), destino.get("reino"), destino.get("regiao"),
                ) if v
            }
            if locais & territorios:
                afetadas.append(rota)
        return afetadas

    def processar_sancoes(self):
        agora = datetime.now(timezone.utc)
        processadas = 0
        bloqueadas = 0
        for sancao in self.sancoes.find({"status": "ativa"}):
            if sancao.get("expira_em") and sancao["expira_em"] <= agora:
                self.sancoes.update_one({"_id": sancao["_id"]}, {"$set": {"status": "encerrada", "encerrada_em": agora}})
                continue

            territorios = self._territorios(sancao)
            tipo = str(sancao.get("tipo", "sancao")).lower()
            severidade = min(1.0, self._numero(sancao.get("severidade"), 0.5))
            processadas += 1

            for rota in self._rotas_afetadas(territorios):
                if tipo in {"embargo", "bloqueio_total"}:
                    self.rotas.update_one({"_id": rota["_id"]}, {"$set": {"status": "bloqueada", "motivo_interrupcao": "embargo_economico", "impacto_diplomatico": severidade}})
                    bloqueadas += 1
                else:
                    tarifa = self._numero(rota.get("tarifa_percentual"))
                    nova_tarifa = min(1.0, tarifa + (0.10 * severidade))
                    self.rotas.update_one({"_id": rota["_id"]}, {"$set": {"tarifa_percentual": nova_tarifa, "impacto_diplomatico": severidade}})

        return {"sancoes_processadas": processadas, "rotas_bloqueadas": bloqueadas}

    def processar_tratados(self):
        agora = datetime.now(timezone.utc)
        processados = 0
        beneficios = 0
        for tratado in self.acordos.find({"status": "ativo"}):
            if tratado.get("expira_em") and tratado["expira_em"] <= agora:
                self.acordos.update_one({"_id": tratado["_id"]}, {"$set": {"status": "expirado", "encerrado_em": agora}})
                continue

            territorios = self._territorios(tratado)
            if len(territorios) < 2:
                continue

            tipo = str(tratado.get("tipo", "comercial")).lower()
            reducao = min(0.95, self._numero(tratado.get("reducao_tarifaria"), 0.50))
            processados += 1

            for rota in self._rotas_afetadas(territorios):
                origem = rota.get("territorio_origem") or {}
                destino = rota.get("territorio_destino") or {}
                paises = {str(v) for v in (origem.get("pais"), destino.get("pais")) if v}
                if not paises or not paises.issubset(territorios):
                    continue

                tarifa = self._numero(rota.get("tarifa_percentual"))
                nova_tarifa = tarifa * (1.0 - reducao)
                campos = {"tarifa_percentual": nova_tarifa, "tratado_diplomatico_id": str(tratado["_id"]), "beneficio_diplomatico": tipo}
                if tipo in {"alianca", "livre_comercio", "comercial"} and rota.get("status") == "bloqueada":
                    campos["status"] = "ativa"
                self.rotas.update_one({"_id": rota["_id"]}, {"$set": campos})
                beneficios += 1

        return {"tratados_processados": processados, "rotas_beneficiadas": beneficios}

    def executar_ciclo(self):
        sancoes = self.processar_sancoes()
        tratados = self.processar_tratados()
        return {**sancoes, **tratados}
