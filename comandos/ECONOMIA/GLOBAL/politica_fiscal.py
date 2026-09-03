from datetime import datetime, timezone


class MotorPoliticaFiscal:
    """Orçamento público, tributação, gastos e dívida soberana."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.governos = db["Economia_Governos"]
        self.orcamentos = db["Economia_Orcamentos_Publicos"]
        self.dividas = db["Economia_Divida_Publica"]
        self.historico = db["Economia_Fiscal_Historico"]

    def configurar_governo(self, governo, imposto_renda=0.10, imposto_consumo=0.05, gasto_planejado=0.0, limite_divida=1_000_000_000.0):
        doc = {"governo": str(governo), "imposto_renda": max(0.0, min(0.90, float(imposto_renda))), "imposto_consumo": max(0.0, min(0.90, float(imposto_consumo))), "gasto_planejado_bronze": max(0.0, float(gasto_planejado)), "limite_divida_bronze": max(0.0, float(limite_divida)), "atualizado_em": datetime.now(timezone.utc)}
        self.orcamentos.update_one({"governo": doc["governo"]}, {"$set": doc, "$setOnInsert": {"receita_bronze": 0.0, "gasto_bronze": 0.0, "saldo_fiscal_bronze": 0.0}}, upsert=True)
        return self.orcamentos.find_one({"governo": doc["governo"]})

    def registrar_receita(self, governo, valor_bronze, origem="tributos"):
        valor = max(0.0, float(valor_bronze)); agora = datetime.now(timezone.utc)
        self.orcamentos.update_one({"governo": str(governo)}, {"$inc": {"receita_bronze": valor, f"receitas_por_origem.{origem}": valor}, "$set": {"atualizado_em": agora}}, upsert=True)
        return valor

    def registrar_gasto(self, governo, valor_bronze, destino="servicos_publicos"):
        valor = max(0.0, float(valor_bronze)); agora = datetime.now(timezone.utc)
        self.orcamentos.update_one({"governo": str(governo)}, {"$inc": {"gasto_bronze": valor, f"gastos_por_destino.{destino}": valor}, "$set": {"atualizado_em": agora}}, upsert=True)
        return valor

    def emitir_divida(self, governo, valor_bronze, juros=0.05, prazo_ciclos=30):
        valor = max(1.0, float(valor_bronze)); governo = str(governo); orc = self.orcamentos.find_one({"governo": governo}) or {}
        atual = sum(float(x.get("principal_restante_bronze", 0)) for x in self.dividas.find({"governo": governo, "status": "ativa"}))
        if atual + valor > float(orc.get("limite_divida_bronze", 1_000_000_000.0)):
            return {"erro": "limite_divida_excedido", "divida_atual": atual}
        doc = {"governo": governo, "principal_original_bronze": valor, "principal_restante_bronze": valor, "juros": max(0.0, min(1.0, float(juros))), "prazo_ciclos": max(1, int(prazo_ciclos)), "ciclos_restantes": max(1, int(prazo_ciclos)), "status": "ativa", "criada_em": datetime.now(timezone.utc)}
        self.dividas.insert_one(doc); self.registrar_receita(governo, valor, "emissao_divida")
        return doc

    def processar_ciclo(self, macro=None):
        macro = macro or {}; resultado = []
        for orc in self.orcamentos.find():
            governo = orc["governo"]
            receita = float(orc.get("receita_bronze", 0.0)); gasto = float(orc.get("gasto_bronze", 0.0)); saldo = receita - gasto
            divida_total = 0.0; juros_pagos = 0.0
            for divida in self.dividas.find({"governo": governo, "status": "ativa"}):
                principal = float(divida.get("principal_restante_bronze", 0)); juros = principal * float(divida.get("juros", 0)) / max(1, int(divida.get("prazo_ciclos", 1))); amortizacao = principal / max(1, int(divida.get("ciclos_restantes", 1)))
                pagamento = juros + amortizacao
                if saldo >= pagamento:
                    saldo -= pagamento; juros_pagos += juros; principal -= amortizacao; ciclos = int(divida.get("ciclos_restantes", 1)) - 1
                    status = "quitada" if principal <= 0.01 or ciclos <= 0 else "ativa"
                    self.dividas.update_one({"_id": divida["_id"]}, {"$set": {"principal_restante_bronze": max(0.0, principal), "ciclos_restantes": max(0, ciclos), "status": status, "atualizada_em": datetime.now(timezone.utc)}})
                divida_total += max(0.0, principal)
            deficit = max(0.0, -saldo)
            if deficit > 0:
                emissao = self.emitir_divida(governo, deficit, prazo_ciclos=30)
                if "erro" not in emissao: divida_total += deficit
            self.orcamentos.update_one({"_id": orc["_id"]}, {"$set": {"saldo_fiscal_bronze": saldo, "divida_total_bronze": divida_total, "juros_pagos_bronze": juros_pagos, "ultimo_ciclo": datetime.now(timezone.utc), "receita_bronze": 0.0, "gasto_bronze": 0.0}})
            resultado.append({"governo": governo, "receita_bronze": receita, "gasto_bronze": gasto, "saldo_fiscal_bronze": saldo, "divida_total_bronze": divida_total, "deficit_bronze": deficit, "juros_pagos_bronze": juros_pagos})
        if resultado: self.historico.insert_one({"data": datetime.now(timezone.utc), "resultados": resultado, "macro": macro})
        return resultado
