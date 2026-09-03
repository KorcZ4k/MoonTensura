from datetime import datetime, timezone, timedelta
from bson import ObjectId


class MotorCredito:
    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.emprestimos = db["Economia_Emprestimos"]
        self.bancos = db["Economia_Bancos"]
        self.hunos = db["Hunos"]
        self.execucoes = db["Economia_Execucoes"]

    def _perfil(self, devedor_id):
        ativos = list(self.emprestimos.find({"devedor_id": str(devedor_id), "status": "ativo"}))
        atrasados = list(self.emprestimos.find({"devedor_id": str(devedor_id), "status": "inadimplente"}))
        quitados = self.emprestimos.count_documents({"devedor_id": str(devedor_id), "status": "quitado"})
        divida = sum(float(x.get("saldo_bronze", 0)) for x in ativos + atrasados)
        score = 750.0 + min(100.0, quitados * 15.0) - len(atrasados) * 180.0 - min(350.0, divida / 1000.0)
        return {"score": max(0.0, min(1000.0, score)), "divida": divida, "atrasados": len(atrasados), "quitados": quitados}

    def _conta_hunos(self, devedor_id):
        return self.hunos.find_one({"ID": str(devedor_id)}) or self.hunos.find_one({"id": str(devedor_id)}) or self.hunos.find_one({"ID": int(devedor_id) if str(devedor_id).isdigit() else devedor_id})

    def solicitar(self, devedor_id, banco_nome, valor, parcelas=10, garantia=0.0, dias_entre_parcelas=1):
        valor = float(valor); parcelas = max(1, int(parcelas)); garantia = max(0.0, float(garantia))
        banco = self.bancos.find_one({"nome": banco_nome})
        if not banco or valor <= 0: return {"erro": "banco_ou_valor_invalido"}
        if float(banco.get("reservas_bronze", 0)) < valor: return {"erro": "liquidez_bancaria_insuficiente"}
        perfil = self._perfil(devedor_id)
        if perfil["score"] < 250: return {"erro": "credito_negado", "score": perfil["score"]}
        taxa_base = float((self.motor.relatorio_global() or {}).get("taxa_juros", 0.05)); risco = (1000.0 - perfil["score"]) / 1000.0 * 0.25; cobertura = min(0.15, garantia / max(valor, 1.0) * 0.15)
        taxa = max(0.005, taxa_base + risco - cobertura); total = valor * (1 + taxa); parcela = total / parcelas; agora = datetime.now(timezone.utc)
        doc = {"devedor_id": str(devedor_id), "banco_nome": banco_nome, "principal_bronze": valor, "saldo_bronze": total, "taxa_juros": taxa, "parcelas_total": parcelas, "parcelas_restantes": parcelas, "valor_parcela_bronze": parcela, "garantia_bronze": garantia, "status": "ativo", "atrasos": 0, "dias_entre_parcelas": max(1, int(dias_entre_parcelas)), "proximo_vencimento": agora + timedelta(days=max(1, int(dias_entre_parcelas))), "criado_em": agora}
        resultado = self.emprestimos.insert_one(doc); doc["_id"] = resultado.inserted_id
        conta = self._conta_hunos(devedor_id)
        if conta:
            self.hunos.update_one({"_id": conta["_id"]}, {"$inc": {"hunos": valor}})
        else:
            self.hunos.insert_one({"ID": str(devedor_id), "hunos": valor})
        self.bancos.update_one({"_id": banco["_id"]}, {"$inc": {"reservas_bronze": -valor, "emprestimos_bronze": valor}})
        return {"emprestimo": doc, "score": perfil["score"]}

    def pagar_parcela(self, devedor_id, emprestimo_id):
        try: oid = ObjectId(str(emprestimo_id))
        except Exception: return {"erro": "id_invalido"}
        emp = self.emprestimos.find_one({"_id": oid, "devedor_id": str(devedor_id), "status": {"$in": ["ativo", "inadimplente"]}})
        if not emp: return {"erro": "emprestimo_inexistente"}
        valor = min(float(emp["valor_parcela_bronze"]), float(emp["saldo_bronze"])); conta = self._conta_hunos(devedor_id); saldo = float((conta or {}).get("hunos", 0))
        if saldo < valor: return {"erro": "saldo_insuficiente", "necessario": valor}
        novo_saldo = max(0.0, float(emp["saldo_bronze"]) - valor); restantes = max(0, int(emp["parcelas_restantes"]) - 1); status = "quitado" if novo_saldo <= 0.01 or restantes == 0 else "ativo"; agora = datetime.now(timezone.utc)
        self.hunos.update_one({"_id": conta["_id"]}, {"$inc": {"hunos": -valor}})
        self.bancos.update_one({"nome": emp["banco_nome"]}, {"$inc": {"reservas_bronze": valor, "emprestimos_bronze": -min(valor, float(emp["principal_bronze"]))}})
        self.emprestimos.update_one({"_id": oid}, {"$set": {"saldo_bronze": novo_saldo, "parcelas_restantes": restantes, "status": status, "atrasos": 0, "ultimo_pagamento": agora, "proximo_vencimento": agora + timedelta(days=max(1, int(emp.get("dias_entre_parcelas", 1))))}})
        return {"pago": valor, "saldo": novo_saldo, "status": status}

    def processar_ciclo(self):
        agora = datetime.now(timezone.utc); inadimplentes = 0; vencidos = 0; execucoes = 0
        for emp in self.emprestimos.find({"status": {"$in": ["ativo", "inadimplente"]}}):
            vencimento = emp.get("proximo_vencimento")
            if vencimento and vencimento > agora: continue
            vencidos += 1; atrasos = int(emp.get("atrasos", 0)) + 1; status = "inadimplente" if atrasos >= 3 else "ativo"; multa = float(emp.get("valor_parcela_bronze", 0)) * 0.05 if status == "inadimplente" else 0.0
            novo_saldo = float(emp.get("saldo_bronze", 0)) + multa
            self.emprestimos.update_one({"_id": emp["_id"]}, {"$set": {"atrasos": atrasos, "status": status, "saldo_bronze": novo_saldo, "ultimo_ciclo": agora, "proximo_vencimento": agora + timedelta(days=max(1, int(emp.get("dias_entre_parcelas", 1))))}})
            if status == "inadimplente":
                inadimplentes += 1
                if atrasos >= 6:
                    garantia = min(float(emp.get("garantia_bronze", 0)), novo_saldo)
                    self.execucoes.insert_one({"emprestimo_id": str(emp["_id"]), "devedor_id": emp["devedor_id"], "valor_executado_bronze": garantia, "data": agora, "motivo": "inadimplencia_prolongada"})
                    self.emprestimos.update_one({"_id": emp["_id"]}, {"$set": {"status": "executado", "saldo_bronze": max(0.0, novo_saldo - garantia)}}); execucoes += 1
        return {"inadimplentes": inadimplentes, "vencidos": vencidos, "execucoes": execucoes}
