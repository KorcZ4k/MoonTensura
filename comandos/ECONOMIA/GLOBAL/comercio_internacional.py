from datetime import datetime, timezone


class MotorComercioInternacional:
    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.acordos = db["Economia_Acordos_Comerciais"]
        self.transacoes = db["Economia_Comercio_Internacional"]
        self.governos = db["Economia_Governos"]
        self.cambio = db["Economia_Cambio"]
        self.rotas = db["Economia_Rotas_Comerciais"]

    def configurar_rota(self, origem, destino, modelo="tradicional", distancia=1.0, tarifa=0.0, risco=0.0):
        modelo = str(modelo).lower()
        if modelo not in {"tradicional", "tempest"}:
            return {"erro": "modelo_invalido"}
        custo_base = 0.05 if modelo == "tempest" else 0.45
        doc = {"origem": str(origem), "destino": str(destino), "modelo": modelo, "distancia": max(0.1, float(distancia)), "tarifa": max(0.0, float(tarifa)), "risco": max(0.0, min(1.0, float(risco))), "custo_logistico_base": custo_base, "atualizado_em": datetime.now(timezone.utc)}
        self.rotas.update_one({"origem": doc["origem"], "destino": doc["destino"]}, {"$set": doc}, upsert=True)
        return doc

    def definir_cambio(self, moeda, bronze_por_unidade, governo_id=None):
        taxa = max(0.000001, float(bronze_por_unidade))
        doc = {"moeda": str(moeda).upper(), "bronze_por_unidade": taxa, "governo_id": str(governo_id) if governo_id is not None else None, "atualizado_em": datetime.now(timezone.utc)}
        self.cambio.update_one({"moeda": doc["moeda"], "governo_id": doc["governo_id"]}, {"$set": doc}, upsert=True)
        return doc

    def converter(self, valor, moeda_origem="BRONZE", moeda_destino="BRONZE"):
        origem = self.cambio.find_one({"moeda": str(moeda_origem).upper()}) if str(moeda_origem).upper() != "BRONZE" else {"bronze_por_unidade": 1.0}
        destino = self.cambio.find_one({"moeda": str(moeda_destino).upper()}) if str(moeda_destino).upper() != "BRONZE" else {"bronze_por_unidade": 1.0}
        if not origem or not destino: return {"erro": "moeda_nao_configurada"}
        bronze = float(valor) * float(origem["bronze_por_unidade"])
        return {"valor": bronze / float(destino["bronze_por_unidade"]), "bronze_equivalente": bronze}

    def _rota(self, origem, destino):
        return self.rotas.find_one({"origem": str(origem), "destino": str(destino)})

    def registrar_transacao(self, origem, destino, valor_bronze, quantidade=1, categoria="mercadoria", moeda="BRONZE"):
        valor = max(0.0, float(valor_bronze)); rota = self._rota(origem, destino)
        if not rota:
            rota = self.configurar_rota(origem, destino)
        logistica = valor * float(rota.get("custo_logistico_base", 0.45)) * max(0.5, float(rota.get("distancia", 1.0)))
        tarifas = valor * max(0.0, float(rota.get("tarifa", 0.0)))
        risco = valor * max(0.0, float(rota.get("risco", 0.0))) * 0.10
        custo_total = logistica + tarifas + risco
        preco_final = valor + custo_total
        doc = {"origem": str(origem), "destino": str(destino), "valor_exportado_bronze": valor, "quantidade": max(1, int(quantidade)), "categoria": categoria, "moeda": str(moeda).upper(), "custo_logistico_bronze": logistica, "tarifas_bronze": tarifas, "risco_bronze": risco, "custo_total_bronze": custo_total, "preco_final_bronze": preco_final, "modelo_rota": rota.get("modelo"), "data": datetime.now(timezone.utc)}
        self.transacoes.insert_one(doc)
        self.governos.update_one({"governo_id": str(origem)}, {"$inc": {"exportacoes_bronze": valor, "balanca_comercial_bronze": valor, "receita_externa_bronze": preco_final}}, upsert=True)
        self.governos.update_one({"governo_id": str(destino)}, {"$inc": {"importacoes_bronze": valor, "balanca_comercial_bronze": -valor, "despesa_externa_bronze": preco_final}}, upsert=True)
        self.motor.economia.update_one({"_id": "global"}, {"$inc": {"fluxo_capital": valor, "liquidez_ouro": -valor / 10000.0}}, upsert=True)
        return doc

    def balanca_comercial(self, governo_id):
        g = self.governos.find_one({"governo_id": str(governo_id)}) or {}
        exp = float(g.get("exportacoes_bronze", 0)); imp = float(g.get("importacoes_bronze", 0))
        return {"governo_id": str(governo_id), "exportacoes_bronze": exp, "importacoes_bronze": imp, "saldo_bronze": exp - imp, "situacao": "superavit" if exp > imp else "deficit" if imp > exp else "equilibrio"}

    def processar_ciclo(self):
        resultados = []
        for governo in self.governos.find():
            balanca = self.balanca_comercial(governo["governo_id"])
            self.governos.update_one({"_id": governo["_id"]}, {"$set": {"balanca_comercial_bronze": balanca["saldo_bronze"], "situacao_externa": balanca["situacao"], "atualizado_em": datetime.now(timezone.utc)}})
            resultados.append(balanca)
        return resultados
