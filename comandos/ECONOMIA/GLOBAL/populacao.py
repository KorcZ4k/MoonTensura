import math
import random
from datetime import datetime, timezone


class MotorPopulacao:
    """População, renda, consumo, emprego e demanda agregada."""

    CLASSES = {
        "baixa": {"renda_min": 2000, "renda_max": 2500, "propensao_consumo": 0.95, "poupanca": 0.03},
        "media": {"renda_min": 3000, "renda_max": 5000, "propensao_consumo": 0.78, "poupanca": 0.15},
        "alta": {"renda_min": 20000, "renda_max": 50000, "propensao_consumo": 0.55, "poupanca": 0.35},
    }

    NECESSIDADES = {
        "comida": {"peso": 1.00, "elasticidade": 0.15},
        "moradia": {"peso": 0.70, "elasticidade": 0.20},
        "roupas": {"peso": 0.35, "elasticidade": 0.75},
        "itens": {"peso": 0.45, "elasticidade": 1.10},
        "luxo": {"peso": 0.15, "elasticidade": 1.80},
    }

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.populacoes = db["Economia_Populacao"]
        self.consumo = db["Economia_Consumo"]
        self.empregos = db["Economia_Empregos"]

    def configurar_populacao(self, governo_id, quantidade, distribuicao=None):
        distribuicao = distribuicao or {"baixa": 0.70, "media": 0.25, "alta": 0.05}
        total_distribuicao = sum(max(0.0, float(v)) for v in distribuicao.values())
        if total_distribuicao <= 0:
            return {"erro": "distribuicao_invalida"}
        distribuicao = {k: max(0.0, float(v)) / total_distribuicao for k, v in distribuicao.items() if k in self.CLASSES}
        quantidade = max(0, int(quantidade))
        classes = {classe: int(quantidade * percentual) for classe, percentual in distribuicao.items()}
        diferenca = quantidade - sum(classes.values())
        if classes: classes[max(classes, key=classes.get)] += diferenca
        renda_total = 0.0
        for classe, qtd in classes.items():
            dados = self.CLASSES[classe]
            renda_media = (dados["renda_min"] + dados["renda_max"]) / 2
            renda_total += qtd * renda_media
        doc = {
            "governo_id": str(governo_id), "quantidade": quantidade, "classes": classes,
            "distribuicao": distribuicao, "renda_mensal_total_bronze": renda_total,
            "empregados": quantidade, "desempregados": 0, "taxa_desemprego": 0.0,
            "atualizado_em": datetime.now(timezone.utc)
        }
        self.populacoes.update_one({"governo_id": str(governo_id)}, {"$set": doc}, upsert=True)
        return doc

    def definir_desemprego(self, governo_id, taxa):
        taxa = min(1.0, max(0.0, float(taxa)))
        populacao = self.populacoes.find_one({"governo_id": str(governo_id)})
        if not populacao: return {"erro": "populacao_inexistente"}
        total = int(populacao.get("quantidade", 0))
        desempregados = int(total * taxa)
        empregados = total - desempregados
        self.populacoes.update_one({"_id": populacao["_id"]}, {"$set": {
            "taxa_desemprego": taxa, "desempregados": desempregados,
            "empregados": empregados, "atualizado_em": datetime.now(timezone.utc)}})
        return {"empregados": empregados, "desempregados": desempregados, "taxa": taxa}

    def poder_de_compra(self, governo_id):
        pop = self.populacoes.find_one({"governo_id": str(governo_id)})
        if not pop: return {"erro": "populacao_inexistente"}
        dados_global = self.motor.relatorio_global()
        indice = max(1.0, float(dados_global.get("indice_precos", 100.0)))
        renda = float(pop.get("renda_mensal_total_bronze", 0))
        empregados = int(pop.get("empregados", 0))
        total = max(1, int(pop.get("quantidade", 1)))
        renda_efetiva = renda * (empregados / total)
        return {"renda_nominal": renda_efetiva, "indice_precos": indice,
                "renda_real": renda_efetiva / (indice / 100.0)}

    def demanda_categoria(self, governo_id, categoria):
        categoria = str(categoria).lower()
        necessidade = self.NECESSIDADES.get(categoria)
        if not necessidade: return {"erro": "categoria_invalida"}
        poder = self.poder_de_compra(governo_id)
        if "erro" in poder: return poder
        base = poder["renda_real"] * necessidade["peso"]
        indice = max(1.0, poder["indice_precos"])
        fator_preco = (100.0 / indice) ** necessidade["elasticidade"]
        demanda = max(0.0, base * fator_preco)
        return {"categoria": categoria, "demanda_bronze": demanda,
                "poder_compra_bronze": poder["renda_real"], "fator_preco": fator_preco}

    def registrar_consumo(self, governo_id, categoria, valor_bronze, quantidade=1):
        valor = max(0.0, float(valor_bronze))
        demanda = self.demanda_categoria(governo_id, categoria)
        if "erro" in demanda: return demanda
        registro = {
            "governo_id": str(governo_id), "categoria": str(categoria).lower(),
            "valor_bronze": valor, "quantidade": max(1, int(quantidade)),
            "demanda_teorica_bronze": demanda["demanda_bronze"],
            "criado_em": datetime.now(timezone.utc)
        }
        self.consumo.insert_one(registro)
        return registro

    def ciclo_consumo(self, governo_id, limite_por_categoria=1000000):
        resultados = []
        for categoria in self.NECESSIDADES:
            demanda = self.demanda_categoria(governo_id, categoria)
            if "erro" in demanda: continue
            gasto = min(float(limite_por_categoria), demanda["demanda_bronze"])
            resultados.append({"categoria": categoria, "demanda": demanda["demanda_bronze"], "gasto_potencial": gasto})
        return resultados

    def aplicar_choque(self, governo_id, tipo, intensidade):
        pop = self.populacoes.find_one({"governo_id": str(governo_id)})
        if not pop: return {"erro": "populacao_inexistente"}
        intensidade = max(-1.0, min(1.0, float(intensidade)))
        if tipo == "emprego":
            nova_taxa = max(0.0, min(1.0, float(pop.get("taxa_desemprego", 0)) - intensidade))
            return self.definir_desemprego(governo_id, nova_taxa)
        if tipo == "renda":
            nova_renda = max(0.0, float(pop.get("renda_mensal_total_bronze", 0)) * (1 + intensidade))
            self.populacoes.update_one({"_id": pop["_id"]}, {"$set": {"renda_mensal_total_bronze": nova_renda, "atualizado_em": datetime.now(timezone.utc)}})
            return {"ok": True, "renda_mensal_total_bronze": nova_renda}
        return {"erro": "choque_invalido"}
