from datetime import datetime, timezone


class MotorGovernoETesouro:
    """Etapa 10: impostos, tesouro, gastos públicos e equilíbrio governamental."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.governos = db["Economia_Governos"]
        self.empresas = db["Economia_Empresas"]
        self.populacoes = db["Economia_Populacoes"]
        self.rotas = db["Economia_Rotas"]
        self.tesouros = db["Economia_Tesouros"]
        self.acontecimentos = db["Economia_Acontecimentos"]

    @staticmethod
    def _numero(valor, padrao=0.0):
        try:
            return max(0.0, float(valor if valor is not None else padrao))
        except (TypeError, ValueError):
            return float(padrao)

    def _registrar(self, guild_id, titulo, descricao, dados, prioridade="normal"):
        self.acontecimentos.insert_one({
            "guild_id": str(guild_id), "tipo": "anuncios_governamentais",
            "titulo": titulo, "descricao": descricao, "dados": dados,
            "prioridade": prioridade, "criado_em": datetime.now(timezone.utc),
            "publicado": False,
        })

    def _obter_tesouro(self, governo):
        consulta = {"guild_id": str(governo.get("guild_id")), "governo_id": str(governo.get("_id"))}
        tesouro = self.tesouros.find_one(consulta)
        if tesouro:
            return tesouro
        documento = {**consulta, "saldo_bronze": 0.0, "receita_acumulada_bronze": 0.0, "despesa_acumulada_bronze": 0.0, "criado_em": datetime.now(timezone.utc)}
        resultado = self.tesouros.insert_one(documento)
        documento["_id"] = resultado.inserted_id
        return documento

    def processar_governo(self, governo):
        guild_id = str(governo.get("guild_id"))
        territorio = governo.get("pais") or governo.get("pais_id") or governo.get("reino") or governo.get("reino_id")
        if not territorio:
            return {"acao": "ignorado", "motivo": "sem_territorio"}

        taxa_empresa = self._numero(governo.get("imposto_empresarial"), 0.10)
        taxa_renda = self._numero(governo.get("imposto_renda"), 0.05)
        gasto_base = self._numero(governo.get("gasto_publico_base_bronze"), 0.0)

        receita_empresas = 0.0
        for empresa in self.empresas.find({"guild_id": guild_id, "status": "ativa"}):
            empresa_territorio = empresa.get("pais") or empresa.get("pais_id") or empresa.get("reino") or empresa.get("reino_id")
            if empresa_territorio != territorio:
                continue
            lucro = self._numero(empresa.get("lucro_atual_bronze"))
            imposto = lucro * taxa_empresa
            if imposto > 0:
                caixa = self._numero(empresa.get("caixa_bronze"))
                pago = min(caixa, imposto)
                self.empresas.update_one({"_id": empresa["_id"]}, {"$inc": {"caixa_bronze": -pago}})
                receita_empresas += pago

        receita_renda = 0.0
        for populacao in self.populacoes.find({"guild_id": guild_id}):
            populacao_territorio = populacao.get("pais") or populacao.get("pais_id") or populacao.get("reino") or populacao.get("reino_id")
            if populacao_territorio != territorio:
                continue
            massa_salarial = self._numero(populacao.get("massa_salarial_bronze"))
            receita_renda += massa_salarial * taxa_renda

        receita_tarifas = 0.0
        for rota in self.rotas.find({"guild_id": guild_id}):
            destino = (rota.get("territorio_destino") or {}).get("pais") or (rota.get("territorio_destino") or {}).get("reino")
            if destino == territorio:
                receita_tarifas += self._numero(rota.get("tarifa_estimada_bronze"))

        receita_total = receita_empresas + receita_renda + receita_tarifas
        tesouro = self._obter_tesouro(governo)
        saldo_atual = self._numero(tesouro.get("saldo_bronze"))

        # O gasto público é limitado pelo caixa para impedir saldo negativo artificial.
        gasto = min(saldo_atual + receita_total, gasto_base)
        saldo_novo = saldo_atual + receita_total - gasto
        superavit = receita_total - gasto

        self.tesouros.update_one(
            {"_id": tesouro["_id"]},
            {"$set": {"saldo_bronze": saldo_novo, "ultimo_ciclo": datetime.now(timezone.utc)}, "$inc": {"receita_acumulada_bronze": receita_total, "despesa_acumulada_bronze": gasto}},
        )

        if receita_total > 0 or gasto > 0:
            situacao = "superávit" if superavit > 0 else ("déficit" if superavit < 0 else "equilíbrio")
            self._registrar(guild_id, "🏛️ Relatório do tesouro", f"O governo de {territorio} encerrou o ciclo com {situacao} fiscal.", {"territorio": territorio, "receita": receita_total, "gasto": gasto, "saldo": saldo_novo, "resultado": superavit})

        return {"acao": "processado", "territorio": territorio, "receita": receita_total, "gasto": gasto, "saldo": saldo_novo, "resultado": superavit}

    def executar_ciclo(self):
        resultados = [self.processar_governo(g) for g in self.governos.find({})]
        processados = [r for r in resultados if r.get("acao") == "processado"]
        return {"governos_processados": len(processados), "receita_total_bronze": sum(r["receita"] for r in processados), "gasto_total_bronze": sum(r["gasto"] for r in processados), "saldo_fiscal_bronze": sum(r["resultado"] for r in processados)}
