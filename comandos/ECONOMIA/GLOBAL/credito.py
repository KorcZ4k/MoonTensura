from datetime import datetime, timezone
from bson import ObjectId


class MotorCredito:
    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.emprestimos = db["Economia_Emprestimos"]
        self.bancos = db["Economia_Bancos"]
        self.hunos = db["Hunos"]

    def _perfil(self, devedor_id):
        ativos = list(self.emprestimos.find({"devedor_id": str(devedor_id), "status": "ativo"}))
        atrasados = list(self.emprestimos.find({"devedor_id": str(devedor_id), "status": "inadimplente"}))
        divida = sum(float(x.get("saldo_bronze", 0)) for x in ativos + atrasados)
        score = max(0.0, min(1000.0, 750.0 - len(atrasados) * 180.0 - min(350.0, divida / 1000.0)))
        return {"score": score, "divida": divida, "atrasados": len(atrasados)}

    def solicitar(self, devedor_id, banco_nome, valor, parcelas=10, garantia=0.0):
        valor = float(valor); parcelas = max(1, int(parcelas)); garantia = max(0.0, float(garantia))
        banco = self.bancos.find_one({"nome": banco_nome})
        if not banco or valor <= 0:
            return {"erro": "banco_ou_valor_invalido"}
        perfil = self._perfil(devedor_id)
        if perfil["score"] < 250:
            return {"erro": "credito_negado", "score": perfil["score"]}
        taxa_base = float((self.motor.relatorio_global() or {}).get("taxa_juros", 0.05))
        risco = (1000.0 - perfil["score"]) / 1000.0 * 0.25
        cobertura = min(0.15, garantia / max(valor, 1.0) * 0.15)
        taxa = max(0.005, taxa_base + risco - cobertura)
        total = valor * (1 + taxa)
        parcela = total / parcelas
        doc = {"devedor_id": str(devedor_id), "banco_nome": banco_nome, "principal_bronze": valor, "saldo_bronze": total, "taxa_juros": taxa, "parcelas_total": parcelas, "parcelas_restantes": parcelas, "valor_parcela_bronze": parcela, "garantia_bronze": garantia, "status": "ativo", "atrasos": 0, "criado_em": datetime.now(timezone.utc)}
        self.emprestimos.insert_one(doc)
        self.bancos.update_one({"_id": banco["_id"]}, {"$inc": {"reservas_bronze": -valor, "emprestimos_bronze": valor}})
        return {"emprestimo": doc, "score": perfil["score"]}

    def pagar_parcela(self, devedor_id, emprestimo_id):
        try: oid = ObjectId(str(emprestimo_id))
        except Exception: return {"erro": "id_invalido"}
        emp = self.emprestimos.find_one({"_id": oid, "devedor_id": str(devedor_id), "status": {"$in": ["ativo", "inadimplente"]}})
        if not emp: return {"erro": "emprestimo_inexistente"}
        valor = min(float(emp["valor_parcela_bronze"]), float(emp["saldo_bronze"]))
        hunos = self.hunos.find_one({"ID": str(devedor_id)}) or self.hunos.find_one({"id": str(devedor_id)})
        saldo = float((hunos or {}).get("hunos", 0))
        if saldo < valor: return {"erro": "saldo_insuficiente", "necessario": valor}
        filtro_hunos = {"_id": hunos["_id"]}
        novo_saldo = max(0.0, float(emp["saldo_bronze"]) - valor)
        restantes = max(0, int(emp["parcelas_restantes"]) - 1)
        status = "quitado" if novo_saldo <= 0.01 or restantes == 0 else "ativo"
        self.hunos.update_one(filtro_hunos, {"$inc": {"hunos": -valor}})
        self.bancos.update_one({"nome": emp["banco_nome"]}, {"$inc": {"reservas_bronze": valor, "emprestimos_bronze": -min(valor, float(emp["principal_bronze"]))}})
        self.emprestimos.update_one({"_id": oid}, {"$set": {"saldo_bronze": novo_saldo, "parcelas_restantes": restantes, "status": status, "ultimo_pagamento": datetime.now(timezone.utc)}})
        return {"pago": valor, "saldo": novo_saldo, "status": status}

    def processar_ciclo(self):
        inadimplentes = 0
        for emp in self.emprestimos.find({"status": "ativo"}):
            atrasos = int(emp.get("atrasos", 0)) + 1
            status = "inadimplente" if atrasos >= 3 else "ativo"
            if status == "inadimplente": inadimplentes += 1
            self.emprestimos.update_one({"_id": emp["_id"]}, {"$set": {"atrasos": atrasos, "status": status, "ultimo_ciclo": datetime.now(timezone.utc)}})
        return inadimplentes
