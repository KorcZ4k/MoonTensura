from datetime import datetime, timezone


class MotorComercioInternacional:
    """Comércio entre governos, balança comercial, tarifas e fluxo de capitais."""

    def __init__(self, db, motor, governo):
        self.db = db
        self.motor = motor
        self.governo = governo
        self.rotas = db["Economia_Rotas_Comerciais"]
        self.transacoes = db["Economia_Comercio_Internacional"]
        self.balancas = db["Economia_Balanca_Comercial"]

    def configurar_rota(self, origem_id, destino_id, distancia=1.0, modelo="tradicional", tarifa_logistica=None):
        modelo = str(modelo).lower()
        if modelo not in {"tradicional", "tempest"}:
            return {"erro": "modelo_invalido"}
        custo_percentual = float(tarifa_logistica) if tarifa_logistica is not None else (0.45 if modelo == "tradicional" else 0.05)
        custo_percentual = min(5.0, max(0.0, custo_percentual))
        chave = f"{origem_id}:{destino_id}"
        doc = {"rota_id": chave, "origem_id": str(origem_id), "destino_id": str(destino_id),
               "distancia": max(0.1, float(distancia)), "modelo": modelo,
               "custo_logistico_percentual": custo_percentual,
               "ativa": True, "atualizado_em": datetime.now(timezone.utc)}
        self.rotas.update_one({"rota_id": chave}, {"$set": doc}, upsert=True)
        return doc

    def _rota(self, origem_id, destino_id):
        return self.rotas.find_one({"origem_id": str(origem_id), "destino_id": str(destino_id), "ativa": True})

    def _atualizar_balanca(self, governo_id, exportacoes=0.0, importacoes=0.0):
        self.balancas.update_one({"governo_id": str(governo_id)}, {"$inc": {
            "exportacoes_bronze": float(exportacoes),
            "importacoes_bronze": float(importacoes)}, "$set": {"atualizado_em": datetime.now(timezone.utc)},
            "$setOnInsert": {"governo_id": str(governo_id), "exportacoes_bronze": 0.0, "importacoes_bronze": 0.0}}, upsert=True)
        doc = self.balancas.find_one({"governo_id": str(governo_id)})
        saldo = float(doc.get("exportacoes_bronze", 0)) - float(doc.get("importacoes_bronze", 0))
        self.balancas.update_one({"_id": doc["_id"]}, {"$set": {"saldo_bronze": saldo}})
        return saldo

    def realizar_comercio(self, origem_id, destino_id, produto, valor_bronze, quantidade=1):
        origem_id, destino_id = str(origem_id), str(destino_id)
        if origem_id == destino_id:
            return {"erro": "comercio_interno"}
        rota = self._rota(origem_id, destino_id)
        if not rota:
            return {"erro": "rota_inexistente"}
        valor = max(1.0, float(valor_bronze))
        quantidade = max(1, int(quantidade))
        carga = valor * quantidade
        custo_logistico = carga * float(rota.get("custo_logistico_percentual", 0.45))
        tarifa_exportacao = self.governo.cobrar_tarifa(origem_id, "exportacao", carga, destino_id)
        tarifa_importacao = self.governo.cobrar_tarifa(destino_id, "importacao", carga, origem_id)
        if "erro" in tarifa_exportacao or "erro" in tarifa_importacao:
            return {"erro": "governo_inexistente"}
        custo_total = carga + custo_logistico + float(tarifa_exportacao["valor"]) + float(tarifa_importacao["valor"])
        self._atualizar_balanca(origem_id, exportacoes=carga)
        self._atualizar_balanca(destino_id, importacoes=carga)
        self.motor.economia.update_one({"_id": "global"}, {"$inc": {
            f"balanca_comercial.{origem_id}": carga,
            f"balanca_comercial.{destino_id}": -carga,
            "fluxo_capital": custo_total,
            "liquidez_ouro": -(carga / 10000.0)}}, upsert=True)
        transacao = {"origem_id": origem_id, "destino_id": destino_id, "produto": str(produto),
                     "quantidade": quantidade, "valor_carga_bronze": carga,
                     "custo_logistico_bronze": custo_logistico,
                     "tarifa_exportacao_bronze": float(tarifa_exportacao["valor"]),
                     "tarifa_importacao_bronze": float(tarifa_importacao["valor"]),
                     "custo_final_bronze": custo_total, "modelo_logistico": rota["modelo"],
                     "criado_em": datetime.now(timezone.utc)}
        self.transacoes.insert_one(transacao)
        return transacao

    def balanca_comercial(self, governo_id):
        doc = self.balancas.find_one({"governo_id": str(governo_id)})
        if not doc:
            return {"governo_id": str(governo_id), "exportacoes_bronze": 0.0, "importacoes_bronze": 0.0, "saldo_bronze": 0.0}
        return doc

    def relatorio_rota(self, origem_id, destino_id):
        rota = self._rota(origem_id, destino_id)
        if not rota:
            return {"erro": "rota_inexistente"}
        return rota
