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

    def registrar_governo(self, governo_id, nome=None, reservas_bronze=0, moeda="BRONZE"):
        doc = {"governo_id": str(governo_id), "nome": nome or str(governo_id), "moeda": str(moeda).upper(), "reservas_internacionais_bronze": max(0.0, float(reservas_bronze)), "exportacoes_bronze": 0.0, "importacoes_bronze": 0.0, "balanca_comercial_bronze": 0.0, "receita_externa_bronze": 0.0, "despesa_externa_bronze": 0.0, "receita_tarifaria_bronze": 0.0, "fluxo_ouro_bronze": 0.0, "atualizado_em": datetime.now(timezone.utc)}
        self.governos.update_one({"governo_id": doc["governo_id"]}, {"$setOnInsert": doc}, upsert=True)
        return self.governos.find_one({"governo_id": doc["governo_id"]})

    def configurar_rota(self, origem, destino, modelo="tradicional", distancia=1.0, tarifa=0.0, risco=0.0):
        modelo = str(modelo).lower()
        if modelo not in {"tradicional", "tempest"}: return {"erro": "modelo_invalido"}
        doc = {"origem": str(origem), "destino": str(destino), "modelo": modelo, "distancia": max(0.1, float(distancia)), "tarifa": max(0.0, min(1.0, float(tarifa))), "risco": max(0.0, min(1.0, float(risco))), "custo_logistico_base": 0.05 if modelo == "tempest" else 0.45, "ativa": True, "atualizado_em": datetime.now(timezone.utc)}
        self.rotas.update_one({"origem": doc["origem"], "destino": doc["destino"]}, {"$set": doc}, upsert=True)
        return doc

    def criar_acordo(self, origem, destino, nome, reducao_tarifa=0.0, livre_comercio=False, ativo=True):
        doc = {"origem": str(origem), "destino": str(destino), "nome": str(nome), "reducao_tarifa": max(0.0, min(1.0, float(reducao_tarifa))), "livre_comercio": bool(livre_comercio), "ativo": bool(ativo), "criado_em": datetime.now(timezone.utc)}
        self.acordos.update_one({"origem": doc["origem"], "destino": doc["destino"], "nome": doc["nome"]}, {"$set": doc}, upsert=True)
        return doc

    def _acordo(self, origem, destino):
        return self.acordos.find_one({"origem": str(origem), "destino": str(destino), "ativo": True}) or self.acordos.find_one({"origem": str(destino), "destino": str(origem), "ativo": True})

    def definir_cambio(self, moeda, bronze_por_unidade, governo_id=None):
        doc = {"moeda": str(moeda).upper(), "bronze_por_unidade": max(0.000001, float(bronze_por_unidade)), "governo_id": str(governo_id) if governo_id is not None else None, "atualizado_em": datetime.now(timezone.utc)}
        self.cambio.update_one({"moeda": doc["moeda"], "governo_id": doc["governo_id"]}, {"$set": doc}, upsert=True)
        return doc

    def converter(self, valor, moeda_origem="BRONZE", moeda_destino="BRONZE"):
        origem = self.cambio.find_one({"moeda": str(moeda_origem).upper()}) if str(moeda_origem).upper() != "BRONZE" else {"bronze_por_unidade": 1.0}
        destino = self.cambio.find_one({"moeda": str(moeda_destino).upper()}) if str(moeda_destino).upper() != "BRONZE" else {"bronze_por_unidade": 1.0}
        if not origem or not destino: return {"erro": "moeda_nao_configurada"}
        bronze = float(valor) * float(origem["bronze_por_unidade"])
        return {"valor": bronze / float(destino["bronze_por_unidade"]), "bronze_equivalente": bronze}

    def _rota(self, origem, destino):
        return self.rotas.find_one({"origem": str(origem), "destino": str(destino), "ativa": {"$ne": False}})

    def registrar_transacao(self, origem, destino, valor_bronze, quantidade=1, categoria="mercadoria", moeda="BRONZE"):
        valor = max(0.0, float(valor_bronze)); rota = self._rota(origem, destino)
        if not rota: rota = self.configurar_rota(origem, destino)
        acordo = self._acordo(origem, destino); tarifa_taxa = float(rota.get("tarifa", 0.0))
        if acordo: tarifa_taxa = 0.0 if acordo.get("livre_comercio") else tarifa_taxa * (1.0 - float(acordo.get("reducao_tarifa", 0.0)))
        logistica = valor * float(rota.get("custo_logistico_base", 0.45)) * max(0.5, float(rota.get("distancia", 1.0)))
        tarifas = valor * tarifa_taxa; risco = valor * float(rota.get("risco", 0.0)) * 0.10; custo_total = logistica + tarifas + risco; preco_final = valor + custo_total
        origem_doc = self.governos.find_one({"governo_id": str(origem)}) or self.registrar_governo(origem)
        destino_doc = self.governos.find_one({"governo_id": str(destino)}) or self.registrar_governo(destino)
        if float(destino_doc.get("reservas_internacionais_bronze", 0.0)) < preco_final:
            return {"erro": "reservas_internacionais_insuficientes", "necessario": preco_final, "disponivel": float(destino_doc.get("reservas_internacionais_bronze", 0.0))}
        agora = datetime.now(timezone.utc)
        doc = {"origem": str(origem), "destino": str(destino), "valor_exportado_bronze": valor, "quantidade": max(1, int(quantidade)), "categoria": categoria, "moeda": str(moeda).upper(), "custo_logistico_bronze": logistica, "tarifas_bronze": tarifas, "risco_bronze": risco, "custo_total_bronze": custo_total, "preco_final_bronze": preco_final, "modelo_rota": rota.get("modelo"), "acordo": acordo.get("nome") if acordo else None, "data": agora}
        self.transacoes.insert_one(doc)
        self.governos.update_one({"governo_id": str(origem)}, {"$inc": {"reservas_internacionais_bronze": valor, "exportacoes_bronze": valor, "balanca_comercial_bronze": valor, "receita_externa_bronze": preco_final, "fluxo_ouro_bronze": valor}, "$set": {"atualizado_em": agora}})
        self.governos.update_one({"governo_id": str(destino)}, {"$inc": {"reservas_internacionais_bronze": -preco_final, "importacoes_bronze": valor, "balanca_comercial_bronze": -valor, "despesa_externa_bronze": preco_final, "receita_tarifaria_bronze": tarifas, "fluxo_ouro_bronze": -preco_final}, "$set": {"atualizado_em": agora}})
        self.motor.economia.update_one({"_id": "global"}, {"$inc": {"fluxo_capital": preco_final, "liquidez_ouro": -valor / 10000.0}}, upsert=True)
        return doc

    def balanca_comercial(self, governo_id):
        g = self.governos.find_one({"governo_id": str(governo_id)}) or {}
        exp, imp = float(g.get("exportacoes_bronze", 0)), float(g.get("importacoes_bronze", 0))
        return {"governo_id": str(governo_id), "exportacoes_bronze": exp, "importacoes_bronze": imp, "saldo_bronze": exp - imp, "reservas_internacionais_bronze": float(g.get("reservas_internacionais_bronze", 0)), "situacao": "superavit" if exp > imp else "deficit" if imp > exp else "equilibrio"}

    def processar_ciclo(self):
        resultados = []
        for governo in self.governos.find():
            balanca = self.balanca_comercial(governo["governo_id"])
            self.governos.update_one({"_id": governo["_id"]}, {"$set": {"balanca_comercial_bronze": balanca["saldo_bronze"], "situacao_externa": balanca["situacao"], "atualizado_em": datetime.now(timezone.utc)}})
            resultados.append(balanca)
        return resultados
