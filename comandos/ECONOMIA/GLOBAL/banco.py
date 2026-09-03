from datetime import datetime, timezone, timedelta


class MotorFinanceiro:
    """Crédito, empréstimos, juros, reservas e inadimplência."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.bancos = db["Economia_Bancos"]
        self.contas = db["Economia_Contas"]
        self.emprestimos = db["Economia_Emprestimos"]
        self.transacoes = db["Economia_Transacoes_Financeiras"]

    def criar_banco(self, banco_id, nome, reservas_bronze=1_000_000, taxa_reserva=0.20, taxa_juros=0.05):
        doc = {
            "banco_id": str(banco_id), "nome": str(nome),
            "reservas_bronze": max(0.0, float(reservas_bronze)),
            "depositos_bronze": 0.0, "credito_concedido_bronze": 0.0,
            "taxa_reserva": min(1.0, max(0.0, float(taxa_reserva))),
            "taxa_juros": max(0.0, float(taxa_juros)),
            "status": "ativo", "atualizado_em": datetime.now(timezone.utc)
        }
        self.bancos.update_one({"banco_id": doc["banco_id"]}, {"$set": doc}, upsert=True)
        return self.bancos.find_one({"banco_id": doc["banco_id"]})

    def abrir_conta(self, banco_id, titular_id, tipo_titular="jogador"):
        banco = self.bancos.find_one({"banco_id": str(banco_id), "status": "ativo"})
        if not banco: return {"erro": "banco_inexistente"}
        filtro = {"banco_id": str(banco_id), "titular_id": str(titular_id)}
        self.contas.update_one(filtro, {"$setOnInsert": {
            **filtro, "tipo_titular": tipo_titular, "saldo_bronze": 0.0,
            "criada_em": datetime.now(timezone.utc)
        }}, upsert=True)
        return self.contas.find_one(filtro)

    def depositar(self, banco_id, titular_id, valor_bronze):
        valor = max(0.0, float(valor_bronze))
        if valor <= 0: return {"erro": "valor_invalido"}
        conta = self.abrir_conta(banco_id, titular_id)
        if "erro" in conta: return conta
        self.contas.update_one({"_id": conta["_id"]}, {"$inc": {"saldo_bronze": valor}})
        self.bancos.update_one({"banco_id": str(banco_id)}, {"$inc": {"depositos_bronze": valor, "reservas_bronze": valor}})
        return {"ok": True, "valor": valor}

    def sacar(self, banco_id, titular_id, valor_bronze):
        valor = max(0.0, float(valor_bronze))
        conta = self.contas.find_one({"banco_id": str(banco_id), "titular_id": str(titular_id)})
        banco = self.bancos.find_one({"banco_id": str(banco_id), "status": "ativo"})
        if not conta or not banco: return {"erro": "conta_ou_banco_inexistente"}
        if float(conta.get("saldo_bronze", 0)) < valor: return {"erro": "saldo_insuficiente"}
        if float(banco.get("reservas_bronze", 0)) < valor: return {"erro": "liquidez_insuficiente"}
        self.contas.update_one({"_id": conta["_id"]}, {"$inc": {"saldo_bronze": -valor}})
        self.bancos.update_one({"_id": banco["_id"]}, {"$inc": {"depositos_bronze": -valor, "reservas_bronze": -valor}})
        return {"ok": True, "valor": valor}

    def conceder_emprestimo(self, banco_id, devedor_id, principal_bronze, parcelas=12, taxa_juros=None, tipo_devedor="empresa"):
        banco = self.bancos.find_one({"banco_id": str(banco_id), "status": "ativo"})
        if not banco: return {"erro": "banco_inexistente"}
        principal = max(0.0, float(principal_bronze))
        if principal <= 0 or int(parcelas) <= 0: return {"erro": "dados_invalidos"}
        reservas = float(banco.get("reservas_bronze", 0))
        reserva_minima = float(banco.get("depositos_bronze", 0)) * float(banco.get("taxa_reserva", 0.20))
        credito_disponivel = max(0.0, reservas - reserva_minima)
        if principal > credito_disponivel: return {"erro": "credito_indisponivel", "disponivel": credito_disponivel}
        juros = float(taxa_juros if taxa_juros is not None else banco.get("taxa_juros", 0.05))
        total = principal * (1 + juros)
        parcela = total / int(parcelas)
        doc = {
            "banco_id": str(banco_id), "devedor_id": str(devedor_id), "tipo_devedor": tipo_devedor,
            "principal_bronze": principal, "saldo_devedor_bronze": total,
            "taxa_juros": juros, "parcelas_total": int(parcelas), "parcelas_pagas": 0,
            "valor_parcela_bronze": parcela, "status": "ativo",
            "criado_em": datetime.now(timezone.utc),
            "proximo_vencimento": datetime.now(timezone.utc) + timedelta(days=30)
        }
        self.emprestimos.insert_one(doc)
        self.bancos.update_one({"_id": banco["_id"]}, {"$inc": {"reservas_bronze": -principal, "credito_concedido_bronze": principal}})
        return doc

    def pagar_parcela(self, emprestimo_id, valor_bronze):
        emprestimo = self.emprestimos.find_one({"_id": emprestimo_id, "status": "ativo"})
        if not emprestimo: return {"erro": "emprestimo_inexistente"}
        valor = max(0.0, float(valor_bronze))
        saldo = max(0.0, float(emprestimo["saldo_devedor_bronze"]) - valor)
        parcelas_pagas = int(emprestimo.get("parcelas_pagas", 0)) + 1
        status = "quitado" if saldo <= 0 else "ativo"
        self.emprestimos.update_one({"_id": emprestimo_id}, {"$set": {
            "saldo_devedor_bronze": saldo, "parcelas_pagas": parcelas_pagas,
            "status": status, "proximo_vencimento": datetime.now(timezone.utc) + timedelta(days=30)
        }})
        self.bancos.update_one({"banco_id": emprestimo["banco_id"]}, {"$inc": {"reservas_bronze": valor, "credito_concedido_bronze": -min(valor, float(emprestimo["principal_bronze"]))}})
        return {"ok": True, "saldo": saldo, "status": status}

    def processar_vencimentos(self):
        agora = datetime.now(timezone.utc)
        inadimplentes = 0
        for emprestimo in self.emprestimos.find({"status": "ativo", "proximo_vencimento": {"$lt": agora}}):
            self.emprestimos.update_one({"_id": emprestimo["_id"]}, {"$set": {"status": "inadimplente"}})
            inadimplentes += 1
        return inadimplentes

    def relatorio_banco(self, banco_id):
        banco = self.bancos.find_one({"banco_id": str(banco_id)})
        if not banco: return {"erro": "banco_inexistente"}
        emprestimos = list(self.emprestimos.find({"banco_id": str(banco_id)}))
        inadimplencia = sum(1 for e in emprestimos if e.get("status") == "inadimplente")
        return {"banco": banco, "emprestimos": len(emprestimos), "inadimplentes": inadimplencia}
