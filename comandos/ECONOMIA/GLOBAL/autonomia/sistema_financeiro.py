from datetime import datetime, timezone


class MotorFinanceiroAutonomo:
    """Etapa 7: crédito empresarial, juros, inadimplência e investimentos NPC."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.empresas = db["Economia_Empresas"]
        self.creditos = db["Economia_Creditos"]
        self.investimentos = db["Economia_Investimentos"]
        self.acontecimentos = db["Economia_Acontecimentos"]

    @staticmethod
    def _numero(valor, padrao=0.0):
        try:
            return float(valor if valor is not None else padrao)
        except (TypeError, ValueError):
            return float(padrao)

    def _registrar(self, guild_id, tipo, titulo, descricao, dados, prioridade="normal"):
        self.acontecimentos.insert_one({
            "guild_id": str(guild_id), "tipo": tipo,
            "titulo": titulo, "descricao": descricao,
            "dados": dados, "prioridade": prioridade,
            "criado_em": datetime.now(timezone.utc), "publicado": False,
        })

    def _novo_credito(self, empresa, valor, taxa=0.03, parcelas=12):
        agora = datetime.now(timezone.utc)
        documento = {
            "guild_id": str(empresa.get("guild_id")),
            "empresa_id": str(empresa.get("_id")),
            "principal_bronze": valor,
            "saldo_devedor_bronze": valor,
            "taxa_juros_ciclo": taxa,
            "parcelas_restantes": parcelas,
            "status": "ativo",
            "criado_em": agora,
            "ultimo_pagamento": None,
        }
        self.creditos.insert_one(documento)
        return documento

    def processar_creditos(self):
        processados = 0
        inadimplentes = 0
        quitados = 0

        for credito in self.creditos.find({"status": "ativo"}):
            empresa = self.empresas.find_one({"_id": credito.get("empresa_id")})
            if not empresa:
                continue
            saldo = self._numero(credito.get("saldo_devedor_bronze"))
            taxa = self._numero(credito.get("taxa_juros_ciclo"), 0.03)
            parcelas = max(1, int(self._numero(credito.get("parcelas_restantes"), 1)))
            saldo *= 1 + taxa
            parcela = saldo / parcelas
            caixa = self._numero(empresa.get("caixa_bronze"))
            processados += 1

            if caixa >= parcela:
                novo_saldo = max(0.0, saldo - parcela)
                novas_parcelas = parcelas - 1
                self.empresas.update_one({"_id": empresa["_id"]}, {"$set": {"caixa_bronze": caixa - parcela}})
                campos = {"saldo_devedor_bronze": novo_saldo, "parcelas_restantes": novas_parcelas, "ultimo_pagamento": datetime.now(timezone.utc)}
                if novo_saldo <= 0.01 or novas_parcelas <= 0:
                    campos["status"] = "quitado"
                    quitados += 1
                self.creditos.update_one({"_id": credito["_id"]}, {"$set": campos})
            else:
                inadimplentes += 1
                self.creditos.update_one({"_id": credito["_id"]}, {"$set": {"saldo_devedor_bronze": saldo, "status": "inadimplente", "inadimplente_em": datetime.now(timezone.utc)}})
                self._registrar(empresa.get("guild_id"), "crises_financeiras", "⚠️ Inadimplência empresarial", "Uma empresa não conseguiu realizar o pagamento do seu crédito.", {"empresa_id": str(empresa["_id"]), "divida": saldo}, "alta")

        return {"creditos_processados": processados, "inadimplentes": inadimplentes, "quitados": quitados}

    def avaliar_empresas(self):
        investimentos = 0
        creditos = 0
        for empresa in self.empresas.find({"status": "ativa"}):
            caixa = self._numero(empresa.get("caixa_bronze"))
            receita = self._numero(empresa.get("receita_bronze"))
            custos = self._numero(empresa.get("custos_bronze"))
            lucro = receita - custos
            divida = self.creditos.count_documents({"empresa_id": str(empresa.get("_id")), "status": "ativo"})

            if lucro > 0 and caixa > max(1000, custos * 2):
                valor = min(caixa * 0.10, lucro * 0.5)
                if valor > 0:
                    self.empresas.update_one({"_id": empresa["_id"]}, {"$inc": {"caixa_bronze": -valor}})
                    self.investimentos.insert_one({"guild_id": str(empresa.get("guild_id")), "empresa_id": str(empresa.get("_id")), "valor_bronze": valor, "tipo": "reinvestimento", "criado_em": datetime.now(timezone.utc)})
                    investimentos += 1
            elif lucro > 0 and caixa < max(250, custos * 0.5) and divida == 0:
                valor = max(500.0, custos * 0.75)
                self._novo_credito(empresa, valor)
                self.empresas.update_one({"_id": empresa["_id"]}, {"$inc": {"caixa_bronze": valor}})
                creditos += 1
                self._registrar(empresa.get("guild_id"), "empresas", "🏦 Empresa obteve crédito", "Uma empresa recebeu capital para manter e ampliar suas operações.", {"empresa_id": str(empresa["_id"]), "credito_bronze": valor})
        return {"investimentos": investimentos, "novos_creditos": creditos}

    def executar_ciclo(self):
        creditos = self.processar_creditos()
        avaliacoes = self.avaliar_empresas()
        return {**creditos, **avaliacoes}
