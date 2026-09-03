import random
from datetime import datetime, timezone


class MotorCrisesEconomicas:
    """Motor de choques, crises, recuperação e falência em cascata."""

    TIPOS = {
        "recessao": {"probabilidade": 0.08, "duracao": 8, "demanda": -0.18, "oferta": -0.08, "credito": -0.12, "confianca": -0.20},
        "boom": {"probabilidade": 0.06, "duracao": 6, "demanda": 0.16, "oferta": 0.10, "credito": 0.10, "confianca": 0.18},
        "escassez": {"probabilidade": 0.05, "duracao": 5, "demanda": 0.08, "oferta": -0.25, "credito": 0.00, "confianca": -0.08},
        "crise_financeira": {"probabilidade": 0.025, "duracao": 10, "demanda": -0.22, "oferta": -0.12, "credito": -0.45, "confianca": -0.35},
        "bolha": {"probabilidade": 0.04, "duracao": 5, "demanda": 0.25, "oferta": 0.05, "credito": 0.30, "confianca": 0.28},
        "choque_logistico": {"probabilidade": 0.04, "duracao": 4, "demanda": -0.05, "oferta": -0.20, "credito": -0.03, "confianca": -0.10},
    }

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.crises = db["Economia_Crises"]
        self.empresas = db["Economia_Empresas"]
        self.historico = db["Economia_Crises_Historico"]

    def _estado(self):
        return self.motor.economia.find_one({"_id": "global"}) or {}

    def criar_crise(self, tipo, governo_id=None, intensidade=1.0, duracao=None, origem="sistema"):
        if tipo not in self.TIPOS:
            raise ValueError(f"Tipo de crise inválido: {tipo}")
        modelo = self.TIPOS[tipo]
        intensidade = max(0.1, min(3.0, float(intensidade)))
        doc = {
            "tipo": tipo,
            "governo_id": str(governo_id) if governo_id else None,
            "intensidade": intensidade,
            "duracao_total": int(duracao or modelo["duracao"]),
            "ciclos_restantes": int(duracao or modelo["duracao"]),
            "status": "ativa",
            "origem": origem,
            "criado_em": datetime.now(timezone.utc),
        }
        resultado = self.crises.insert_one(doc)
        doc["_id"] = resultado.inserted_id
        return doc

    def _gerar_evento(self):
        ativos = self.crises.count_documents({"status": "ativa"})
        if ativos:
            return None
        estado = self._estado()
        inflacao = abs(float(estado.get("inflacao_minuto", 0.0)))
        taxa_juros = float(estado.get("taxa_juros", 0.05))
        chance_base = 0.02 + min(0.06, inflacao * 2) + max(0.0, taxa_juros - 0.10) * 0.2
        if random.random() > chance_base:
            return None
        pesos = []
        tipos = []
        for tipo, dados in self.TIPOS.items():
            peso = dados["probabilidade"]
            if tipo == "crise_financeira" and taxa_juros > 0.10:
                peso *= 2
            if tipo == "recessao" and inflacao > 0.01:
                peso *= 1.5
            tipos.append(tipo)
            pesos.append(peso)
        return self.criar_crise(random.choices(tipos, weights=pesos, k=1)[0], origem="aleatorio")

    def _aplicar_efeito_global(self, crise):
        modelo = self.TIPOS[crise["tipo"]]
        intensidade = float(crise.get("intensidade", 1.0))
        fator = lambda chave: float(modelo.get(chave, 0.0)) * intensidade
        estado = self._estado()
        demanda = max(0.0, float(estado.get("demanda_agregada", 0.0)) * (1.0 + fator("demanda")))
        oferta = max(0.0, float(estado.get("oferta_agregada", 0.0)) * (1.0 + fator("oferta")))
        credito = max(0.0, float(estado.get("credito_disponivel_bronze", 0.0)) * (1.0 + fator("credito")))
        confianca = max(0.0, min(100.0, float(estado.get("confianca_economica", 50.0)) + fator("confianca") * 100))
        self.motor.economia.update_one({"_id": "global"}, {"$set": {
            "demanda_agregada": demanda,
            "oferta_agregada": oferta,
            "credito_disponivel_bronze": credito,
            "confianca_economica": confianca,
            "ultima_crise": crise["tipo"],
            "atualizado_em": datetime.now(timezone.utc),
        }})

    def _falencias_em_cascata(self, crise):
        modelo = self.TIPOS[crise["tipo"]]
        if crise["tipo"] not in {"recessao", "crise_financeira", "escassez"}:
            return 0
        intensidade = float(crise.get("intensidade", 1.0))
        falidas = 0
        for empresa in self.empresas.find({"status": {"$ne": "falida"}}):
            receita = max(0.0, float(empresa.get("receita_bronze", empresa.get("receita", 0.0)) or 0.0))
            custos = max(0.0, float(empresa.get("custos_operacionais_bronze", empresa.get("custos", 0.0)) or 0.0))
            caixa = float(empresa.get("caixa_bronze", empresa.get("caixa", 0.0)) or 0.0)
            divida = max(0.0, float(empresa.get("divida_bronze", empresa.get("divida", 0.0)) or 0.0))
            perda = abs(float(modelo.get("demanda", 0.0))) * intensidade * receita
            liquidez = caixa + max(0.0, receita - custos - perda)
            risco = divida / max(1.0, receita + caixa)
            if liquidez <= 0 and random.random() < min(0.85, 0.15 + risco * 0.4):
                self.empresas.update_one({"_id": empresa["_id"]}, {"$set": {"status": "falida", "falida_em": datetime.now(timezone.utc), "motivo_falencia": crise["tipo"]}})
                falidas += 1
        return falidas

    def processar_ciclo(self):
        evento = self._gerar_evento()
        ativas = list(self.crises.find({"status": "ativa"}))
        processadas = []
        falencias = 0
        for crise in ativas:
            self._aplicar_efeito_global(crise)
            falencias += self._falencias_em_cascata(crise)
            restantes = int(crise.get("ciclos_restantes", 1)) - 1
            status = "encerrada" if restantes <= 0 else "ativa"
            self.crises.update_one({"_id": crise["_id"]}, {"$set": {"ciclos_restantes": max(0, restantes), "status": status, "atualizada_em": datetime.now(timezone.utc)}})
            processadas.append({"tipo": crise["tipo"], "status": status, "ciclos_restantes": max(0, restantes)})
        resultado = {"data": datetime.now(timezone.utc), "novo_evento": evento["tipo"] if evento else None, "crises_processadas": len(processadas), "falencias": falencias, "detalhes": processadas}
        self.historico.insert_one(resultado)
        return resultado
