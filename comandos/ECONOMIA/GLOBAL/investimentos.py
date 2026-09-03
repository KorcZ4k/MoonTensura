from datetime import datetime, timezone


class MotorInvestimentos:
    """Mercado de capitais: investimentos produtivos, risco e retorno."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.investimentos = db["Economia_Investimentos"]
        self.empresas = db["Economia_Empresas"]
        self.historico = db["Economia_Investimentos_Historico"]

    def criar_investimento(self, investidor_id, empresa_id, valor_bronze, participacao=0.0, risco=0.10, ciclos=30):
        valor = max(1.0, float(valor_bronze))
        participacao = max(0.0, min(1.0, float(participacao)))
        risco = max(0.0, min(1.0, float(risco)))
        ciclos = max(1, int(ciclos))

        empresa = self.empresas.find_one({"_id": empresa_id})
        if not empresa:
            return {"erro": "empresa_nao_encontrada"}

        patrimonio = max(1.0, float(empresa.get("patrimonio_bronze", 0.0)))
        valuation_pre = max(patrimonio, float(empresa.get("receita_bronze", 0.0)) * 12)
        valuation_pos = valuation_pre + valor
        participacao_calculada = participacao if participacao > 0 else min(0.95, valor / valuation_pos)

        doc = {
            "investidor_id": str(investidor_id),
            "empresa_id": empresa_id,
            "principal_bronze": valor,
            "valor_atual_bronze": valor,
            "participacao": participacao_calculada,
            "risco": risco,
            "ciclos_total": ciclos,
            "ciclos_restantes": ciclos,
            "retorno_acumulado_bronze": 0.0,
            "status": "ativo",
            "criado_em": datetime.now(timezone.utc),
        }
        resultado = self.investimentos.insert_one(doc)
        self.empresas.update_one(
            {"_id": empresa_id},
            {"$inc": {"capital_investido_bronze": valor, "caixa_bronze": valor}, "$set": {"valuation_bronze": valuation_pos, "atualizado_em": datetime.now(timezone.utc)}},
        )
        doc["_id"] = resultado.inserted_id
        return doc

    def retirar_investimento(self, investimento_id):
        investimento = self.investimentos.find_one({"_id": investimento_id, "status": "ativo"})
        if not investimento:
            return {"erro": "investimento_nao_encontrado"}
        self.investimentos.update_one(
            {"_id": investimento_id},
            {"$set": {"status": "retirado", "encerrado_em": datetime.now(timezone.utc)}},
        )
        return investimento

    def processar_ciclo(self, macro=None):
        macro = macro or {}
        crescimento = float(macro.get("crescimento", macro.get("crescimento_economico", 0.0)))
        inflacao = float(self.motor.relatorio_global().get("inflacao_minuto", 0.0))
        resultados = []

        for investimento in self.investimentos.find({"status": "ativo"}):
            empresa = self.empresas.find_one({"_id": investimento["empresa_id"]})
            if not empresa:
                self.investimentos.update_one({"_id": investimento["_id"]}, {"$set": {"status": "perdido", "encerrado_em": datetime.now(timezone.utc)}})
                continue

            risco = float(investimento.get("risco", 0.10))
            margem = float(empresa.get("margem_lucro", empresa.get("margem_liquida", 0.0)))
            receita = max(0.0, float(empresa.get("receita_bronze", 0.0)))
            patrimonio = max(1.0, float(empresa.get("patrimonio_bronze", 1.0)))

            retorno_taxa = (crescimento * 0.35) + (margem * 0.05) - (inflacao * 0.15) - (risco * 0.01)
            retorno_taxa = max(-0.50, min(1.00, retorno_taxa))
            retorno = float(investimento["valor_atual_bronze"]) * retorno_taxa
            novo_valor = max(0.0, float(investimento["valor_atual_bronze"]) + retorno)
            ciclos_restantes = int(investimento.get("ciclos_restantes", 1)) - 1

            insolvencia = receita <= 0 and patrimonio <= 1
            status = "falido" if insolvencia else "concluido" if ciclos_restantes <= 0 else "ativo"

            self.investimentos.update_one(
                {"_id": investimento["_id"]},
                {"$set": {"valor_atual_bronze": novo_valor, "ciclos_restantes": max(0, ciclos_restantes), "status": status, "atualizado_em": datetime.now(timezone.utc)}, "$inc": {"retorno_acumulado_bronze": retorno}},
            )
            resultados.append({"investimento_id": investimento["_id"], "empresa_id": investimento["empresa_id"], "retorno_bronze": retorno, "valor_atual_bronze": novo_valor, "status": status})

        total = sum(x["valor_atual_bronze"] for x in resultados)
        self.motor.economia.update_one(
            {"_id": "global"},
            {"$set": {"capital_investido_bronze": total, "ultimo_ciclo_investimentos": datetime.now(timezone.utc)}},
            upsert=True,
        )
        resultado = {"data": datetime.now(timezone.utc), "investimentos_processados": len(resultados), "capital_total_bronze": total, "resultados": resultados}
        self.historico.insert_one(resultado)
        return resultado
