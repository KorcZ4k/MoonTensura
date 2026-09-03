from datetime import datetime, timezone


class MotorGoverno:
    """Tesouros públicos, impostos, tarifas e políticas fiscais."""

    TIPOS_IMPOSTO = {"venda", "renda", "empresa", "importacao", "exportacao", "propriedade"}

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.governos = db["Economia_Governos"]
        self.impostos = db["Economia_Impostos"]
        self.tesouros = db["Economia_Tesouros"]
        self.gastos = db["Economia_Gastos_Publicos"]

    def criar_governo(self, governo_id, nome, tesouro_inicial=0.0):
        documento = {
            "governo_id": str(governo_id), "nome": str(nome),
            "status": "ativo", "taxas": {tipo: 0.0 for tipo in self.TIPOS_IMPOSTO},
            "tarifas": {"importacao": 0.0, "exportacao": 0.0},
            "criado_em": datetime.now(timezone.utc), "atualizado_em": datetime.now(timezone.utc)
        }
        self.governos.update_one({"governo_id": documento["governo_id"]}, {"$set": documento}, upsert=True)
        self.tesouros.update_one({"governo_id": documento["governo_id"]}, {"$setOnInsert": {
            "governo_id": documento["governo_id"], "saldo_bronze": max(0.0, float(tesouro_inicial)),
            "receita_total_bronze": 0.0, "gasto_total_bronze": 0.0,
            "divida_publica_bronze": 0.0
        }}, upsert=True)
        return self.governos.find_one({"governo_id": documento["governo_id"]})

    def definir_imposto(self, governo_id, tipo, aliquota):
        tipo = str(tipo).lower()
        if tipo not in self.TIPOS_IMPOSTO: return {"erro": "tipo_invalido"}
        aliquota = min(1.0, max(0.0, float(aliquota)))
        resultado = self.governos.update_one({"governo_id": str(governo_id)}, {"$set": {
            f"taxas.{tipo}": aliquota, "atualizado_em": datetime.now(timezone.utc)}})
        if not resultado.matched_count: return {"erro": "governo_inexistente"}
        return {"ok": True, "tipo": tipo, "aliquota": aliquota}

    def definir_tarifa(self, governo_id, tipo, aliquota):
        tipo = str(tipo).lower()
        if tipo not in {"importacao", "exportacao"}: return {"erro": "tipo_invalido"}
        aliquota = min(1.0, max(0.0, float(aliquota)))
        resultado = self.governos.update_one({"governo_id": str(governo_id)}, {"$set": {
            f"tarifas.{tipo}": aliquota, "atualizado_em": datetime.now(timezone.utc)}})
        if not resultado.matched_count: return {"erro": "governo_inexistente"}
        return {"ok": True, "tipo": tipo, "aliquota": aliquota}

    def calcular_imposto(self, governo_id, tipo, base_bronze):
        governo = self.governos.find_one({"governo_id": str(governo_id), "status": "ativo"})
        if not governo: return {"erro": "governo_inexistente"}
        base = max(0.0, float(base_bronze))
        aliquota = float(governo.get("taxas", {}).get(tipo, 0.0))
        valor = base * aliquota
        return {"base": base, "aliquota": aliquota, "valor": valor}

    def arrecadar_imposto(self, governo_id, tipo, base_bronze, origem_id=None, descricao=""):
        calculo = self.calcular_imposto(governo_id, tipo, base_bronze)
        if "erro" in calculo: return calculo
        valor = calculo["valor"]
        self.tesouros.update_one({"governo_id": str(governo_id)}, {"$inc": {
            "saldo_bronze": valor, "receita_total_bronze": valor}}, upsert=True)
        self.impostos.insert_one({
            "governo_id": str(governo_id), "tipo": str(tipo), "base_bronze": calculo["base"],
            "aliquota": calculo["aliquota"], "valor_bronze": valor,
            "origem_id": str(origem_id) if origem_id else None,
            "descricao": descricao, "criado_em": datetime.now(timezone.utc)
        })
        return calculo

    def cobrar_tarifa(self, governo_id, tipo, valor_mercadoria_bronze, origem_id=None):
        governo = self.governos.find_one({"governo_id": str(governo_id), "status": "ativo"})
        if not governo: return {"erro": "governo_inexistente"}
        tipo = str(tipo).lower()
        aliquota = float(governo.get("tarifas", {}).get(tipo, 0.0))
        valor = max(0.0, float(valor_mercadoria_bronze)) * aliquota
        self.tesouros.update_one({"governo_id": str(governo_id)}, {"$inc": {
            "saldo_bronze": valor, "receita_total_bronze": valor}}, upsert=True)
        self.impostos.insert_one({"governo_id": str(governo_id), "tipo": tipo, "base_bronze": float(valor_mercadoria_bronze),
                                  "aliquota": aliquota, "valor_bronze": valor, "origem_id": origem_id,
                                  "criado_em": datetime.now(timezone.utc)})
        return {"valor": valor, "aliquota": aliquota}

    def gastar(self, governo_id, valor_bronze, categoria, descricao=""):
        valor = max(0.0, float(valor_bronze))
        tesouro = self.tesouros.find_one({"governo_id": str(governo_id)})
        if not tesouro: return {"erro": "tesouro_inexistente"}
        saldo = float(tesouro.get("saldo_bronze", 0.0))
        if saldo < valor: return {"erro": "tesouro_insuficiente", "disponivel": saldo}
        self.tesouros.update_one({"_id": tesouro["_id"]}, {"$inc": {"saldo_bronze": -valor, "gasto_total_bronze": valor}})
        self.gastos.insert_one({"governo_id": str(governo_id), "valor_bronze": valor,
                                "categoria": categoria, "descricao": descricao,
                                "criado_em": datetime.now(timezone.utc)})
        return {"ok": True, "valor": valor}

    def relatorio(self, governo_id):
        governo = self.governos.find_one({"governo_id": str(governo_id)})
        tesouro = self.tesouros.find_one({"governo_id": str(governo_id)})
        if not governo: return {"erro": "governo_inexistente"}
        return {"governo": governo, "tesouro": tesouro or {}}
