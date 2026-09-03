import math
from datetime import datetime, timezone
from pymongo import ReturnDocument


class MotorFinanceiroAvancado:
    """Processa dívida pública, risco soberano e estabilidade bancária."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.dividas = db["Economia_Divida_Publica"]
        self.governos = db["Economia_Governos"]
        self.tesouros = db["Economia_Tesouro"]
        self.bancos = db["Economia_Bancos"]
        self.historico = db["Economia_Historico_Financeiro"]

    def _tesouro(self, governo_id):
        return self.tesouros.find_one({"governo_id": str(governo_id)})

    def amortizar_divida(self, governo_id, valor_bronze, divida_id=None):
        valor = max(0.0, float(valor_bronze))
        tesouro = self._tesouro(governo_id)
        if not tesouro or float(tesouro.get("saldo_bronze", 0)) < valor:
            return {"erro": "tesouro_insuficiente"}
        filtro = {"governo_id": str(governo_id), "status": "aberta"}
        if divida_id is not None:
            from bson import ObjectId
            try: filtro["_id"] = ObjectId(str(divida_id))
            except Exception: return {"erro": "id_invalido"}
        dividas = list(self.dividas.find(filtro).sort("ciclos_restantes", 1))
        restante = valor
        pago = 0.0
        for divida in dividas:
            if restante <= 0: break
            saldo = float(divida.get("saldo_bronze", 0))
            parcela = min(restante, saldo)
            novo_saldo = saldo - parcela
            self.dividas.update_one({"_id": divida["_id"]}, {"$set": {"saldo_bronze": novo_saldo, "status": "quitada" if novo_saldo <= 0.01 else "aberta", "ultima_amortizacao": datetime.now(timezone.utc)}})
            restante -= parcela; pago += parcela
        if pago:
            self.tesouros.update_one({"governo_id": str(governo_id)}, {"$inc": {"saldo_bronze": -pago, "gasto_total_bronze": pago}})
        return {"pago_bronze": pago, "restante_bronze": restante}

    def processar_dividas(self):
        resultado = {"vencimentos": 0, "juros": 0.0, "defaults": 0}
        for divida in self.dividas.find({"status": "aberta"}):
            ciclos = int(divida.get("ciclos_restantes", 0)) - 1
            saldo = float(divida.get("saldo_bronze", 0))
            principal = float(divida.get("principal_bronze", 0))
            taxa = float(divida.get("taxa_juros", 0))
            juros_ciclo = principal * taxa / max(1, int(divida.get("prazo_ciclos", 1)))
            saldo += juros_ciclo
            update = {"ciclos_restantes": ciclos, "saldo_bronze": saldo, "ultimo_processamento": datetime.now(timezone.utc)}
            resultado["juros"] += juros_ciclo
            if ciclos <= 0:
                tesouro = self._tesouro(divida["governo_id"])
                caixa = float(tesouro.get("saldo_bronze", 0)) if tesouro else 0.0
                if caixa >= saldo:
                    self.tesouros.update_one({"governo_id": divida["governo_id"]}, {"$inc": {"saldo_bronze": -saldo, "gasto_total_bronze": saldo}})
                    update["status"] = "quitada"; update["saldo_bronze"] = 0.0
                else:
                    update["status"] = "inadimplente"; resultado["defaults"] += 1
                resultado["vencimentos"] += 1
            self.dividas.update_one({"_id": divida["_id"]}, {"$set": update})
        return resultado

    def rating_soberano(self, governo_id):
        tesouro = self._tesouro(governo_id) or {}
        caixa = max(0.0, float(tesouro.get("saldo_bronze", 0)))
        dividas = list(self.dividas.find({"governo_id": str(governo_id)}))
        abertas = [d for d in dividas if d.get("status") == "aberta"]
        inadimplentes = [d for d in dividas if d.get("status") == "inadimplente"]
        divida_total = sum(float(d.get("saldo_bronze", 0)) for d in abertas)
        exposicao = divida_total / max(1.0, caixa + divida_total)
        score = 100.0 - exposicao * 65.0 - len(inadimplentes) * 20.0
        score = max(0.0, min(100.0, score))
        if score >= 90: rating = "AAA"
        elif score >= 80: rating = "AA"
        elif score >= 70: rating = "A"
        elif score >= 60: rating = "BBB"
        elif score >= 50: rating = "BB"
        elif score >= 35: rating = "B"
        elif score >= 20: rating = "CCC"
        else: rating = "D"
        premio_risco = max(0.0, (100.0 - score) / 100.0 * 0.20)
        return {"rating": rating, "score": score, "premio_risco": premio_risco, "divida_total_bronze": divida_total, "inadimplencias": len(inadimplentes)}

    def criar_banco(self, governo_id, nome, reservas_bronze, depositos_bronze=None):
        reservas = max(0.0, float(reservas_bronze))
        depositos = reservas if depositos_bronze is None else max(reservas, float(depositos_bronze))
        doc = {"governo_id": str(governo_id), "nome": str(nome), "reservas_bronze": reservas, "depositos_bronze": depositos, "emprestimos_bronze": 0.0, "status": "estavel", "criado_em": datetime.now(timezone.utc)}
        self.bancos.update_one({"governo_id": str(governo_id), "nome": str(nome)}, {"$set": doc}, upsert=True)
        return doc

    def estabilidade_bancaria(self, governo_id):
        bancos = list(self.bancos.find({"governo_id": str(governo_id)}))
        if not bancos: return {"bancos": 0, "estabilidade": 1.0, "status": "sem_bancos"}
        reservas = sum(float(b.get("reservas_bronze", 0)) for b in bancos)
        depositos = sum(float(b.get("depositos_bronze", 0)) for b in bancos)
        ratio = reservas / max(1.0, depositos)
        if ratio >= 0.20: status = "estavel"
        elif ratio >= 0.10: status = "pressionado"
        elif ratio >= 0.05: status = "fragil"
        else: status = "risco_de_corrida"
        self.bancos.update_many({"governo_id": str(governo_id)}, {"$set": {"status": status, "indice_reserva": ratio, "atualizado_em": datetime.now(timezone.utc)}})
        return {"bancos": len(bancos), "estabilidade": ratio, "status": status, "reservas_bronze": reservas, "depositos_bronze": depositos}

    def processar_ciclo(self):
        dividas = self.processar_dividas()
        governos = set(d["governo_id"] for d in self.dividas.find({}, {"governo_id": 1}))
        governos.update(b["governo_id"] for b in self.bancos.find({}, {"governo_id": 1}))
        ratings = {}
        bancos = {}
        for governo_id in governos:
            ratings[governo_id] = self.rating_soberano(governo_id)
            bancos[governo_id] = self.estabilidade_bancaria(governo_id)
        self.historico.insert_one({"tipo": "ciclo_financeiro", "dividas": dividas, "ratings": ratings, "bancos": bancos, "data": datetime.now(timezone.utc)})
        return {"dividas": dividas, "ratings": ratings, "bancos": bancos}
