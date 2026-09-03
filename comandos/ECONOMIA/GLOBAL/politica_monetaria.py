from datetime import datetime, timezone


class MotorPoliticaMonetaria:
    """Banco central: moeda, reservas, juros, crédito e liquidez."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.bancos_centrais = db["Economia_Bancos_Centrais"]
        self.historico = db["Economia_Monetaria_Historico"]

    def configurar_banco_central(self, governo, reservas_bronze=0.0, taxa_juros=0.05, compulsorio=0.10):
        doc = {
            "governo": str(governo),
            "reservas_bronze": max(0.0, float(reservas_bronze)),
            "base_monetaria_bronze": max(0.0, float(reservas_bronze)),
            "credito_bronze": 0.0,
            "taxa_juros": max(0.0, min(1.0, float(taxa_juros))),
            "compulsorio": max(0.0, min(0.95, float(compulsorio))),
            "politica": "neutra",
            "atualizado_em": datetime.now(timezone.utc),
        }
        self.bancos_centrais.update_one({"governo": doc["governo"]}, {"$setOnInsert": doc, "$set": {"taxa_juros": doc["taxa_juros"], "compulsorio": doc["compulsorio"], "atualizado_em": doc["atualizado_em"]}}, upsert=True)
        return self.bancos_centrais.find_one({"governo": doc["governo"]})

    def definir_juros(self, governo, taxa):
        taxa = max(0.0, min(1.0, float(taxa)))
        return self.bancos_centrais.find_one_and_update(
            {"governo": str(governo)},
            {"$set": {"taxa_juros": taxa, "ultima_decisao": datetime.now(timezone.utc)}},
            upsert=True,
            return_document=True,
        )

    def ajustar_liquidez(self, governo, valor_bronze, operacao="injecao"):
        valor = max(0.0, float(valor_bronze))
        banco = self.bancos_centrais.find_one({"governo": str(governo)})
        if not banco:
            self.configurar_banco_central(governo)
            banco = self.bancos_centrais.find_one({"governo": str(governo)})
        atual = float(banco.get("reservas_bronze", 0.0))
        if operacao == "retirada":
            valor = -min(valor, atual)
            politica = "contracionista"
        elif operacao == "injecao":
            politica = "expansionista"
        else:
            return {"erro": "operacao_invalida"}
        self.bancos_centrais.update_one(
            {"governo": str(governo)},
            {"$inc": {"reservas_bronze": valor, "base_monetaria_bronze": valor}, "$set": {"politica": politica, "atualizado_em": datetime.now(timezone.utc)}},
        )
        return self.bancos_centrais.find_one({"governo": str(governo)})

    def processar_ciclo(self, macro=None):
        macro = macro or {}
        inflacao = float(self.motor.relatorio_global().get("inflacao_minuto", 0.0))
        desemprego = float(macro.get("taxa_desemprego", 0.0))
        demanda = float(macro.get("demanda_agregada_bronze", 0.0))
        resultados = []

        for banco in self.bancos_centrais.find():
            juros = float(banco.get("taxa_juros", 0.05))
            # Regra monetária simples: inflação eleva juros; desemprego elevado reduz.
            ajuste = inflacao * 0.5 - max(0.0, desemprego - 0.08) * 0.1
            novo_juros = max(0.0, min(0.50, juros + ajuste))
            reservas = float(banco.get("reservas_bronze", 0.0))
            compulsorio = float(banco.get("compulsorio", 0.10))
            multiplicador = 1.0 / max(0.05, compulsorio)
            credito_potencial = max(0.0, reservas * multiplicador * (1.0 - novo_juros))
            politica = "contracionista" if novo_juros > juros else "expansionista" if novo_juros < juros else "neutra"

            self.bancos_centrais.update_one(
                {"_id": banco["_id"]},
                {"$set": {"taxa_juros": novo_juros, "credito_bronze": credito_potencial, "politica": politica, "ultimo_ciclo": datetime.now(timezone.utc)}},
            )
            resultados.append({"governo": banco["governo"], "taxa_juros": novo_juros, "reservas_bronze": reservas, "credito_bronze": credito_potencial, "politica": politica})

        reservas = sum(float(x["reservas_bronze"]) for x in resultados)
        credito = sum(float(x["credito_bronze"]) for x in resultados)
        juros_medio = sum(float(x["taxa_juros"]) for x in resultados) / max(1, len(resultados))
        liquidez_relativa = credito / max(1.0, demanda)

        self.motor.economia.update_one(
            {"_id": "global"},
            {"$set": {"reservas_monetarias_bronze": reservas, "credito_disponivel_bronze": credito, "taxa_juros": juros_medio, "liquidez_relativa": liquidez_relativa, "ultimo_ciclo_monetario": datetime.now(timezone.utc)}},
            upsert=True,
        )
        resultado = {"data": datetime.now(timezone.utc), "bancos": resultados, "reservas_bronze": reservas, "credito_bronze": credito, "taxa_juros_media": juros_medio, "liquidez_relativa": liquidez_relativa}
        self.historico.insert_one(resultado)
        return resultado
