from datetime import datetime, timezone


class MotorRecuperacaoEconomica:
    """Recuperação gradual após crises, evitando retornos instantâneos aos níveis anteriores."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.crises = db["Economia_Crises"]
        self.empresas = db["Economia_Empresas"]
        self.historico = db["Economia_Recuperacao"]

    def processar_ciclo(self):
        ativas = self.crises.count_documents({"status": "ativa"})
        estado = self.motor.relatorio_global()

        if ativas > 0:
            resultado = {
                "recuperacao": False,
                "motivo": "crises_ativas",
                "crises_ativas": ativas,
                "data": datetime.now(timezone.utc),
            }
            self.historico.insert_one(resultado)
            return resultado

        confianca = float(estado.get("confianca_economica", 50.0))
        credito = float(estado.get("credito_disponivel_bronze", 0.0))
        reservas = float(estado.get("reservas_monetarias_bronze", 0.0))
        inflacao = float(estado.get("inflacao_minuto", 0.0))

        # Convergência gradual para condições estáveis.
        nova_confianca = confianca + (60.0 - confianca) * 0.08
        novo_credito = credito + max(0.0, reservas * 0.002)
        nova_inflacao = inflacao * 0.92

        self.motor.economia.update_one(
            {"_id": "global"},
            {"$set": {
                "confianca_economica": max(0.0, min(100.0, nova_confianca)),
                "credito_disponivel_bronze": max(0.0, novo_credito),
                "inflacao_minuto": nova_inflacao,
                "fase_recuperacao": "gradual",
                "ultima_recuperacao": datetime.now(timezone.utc),
            }},
            upsert=True,
        )

        recuperadas = 0
        for empresa in self.empresas.find({"status": "falida"}):
            caixa = float(empresa.get("caixa_bronze", empresa.get("caixa", 0.0)) or 0.0)
            receita = float(empresa.get("receita_bronze", empresa.get("receita", 0.0)) or 0.0)
            if caixa > 0 and receita > 0:
                self.empresas.update_one(
                    {"_id": empresa["_id"]},
                    {"$set": {
                        "status": "recuperacao",
                        "recuperacao_em": datetime.now(timezone.utc),
                    }},
                )
                recuperadas += 1

        resultado = {
            "recuperacao": True,
            "confianca_anterior": confianca,
            "confianca_atual": nova_confianca,
            "credito_adicionado": max(0.0, reservas * 0.002),
            "empresas_em_recuperacao": recuperadas,
            "data": datetime.now(timezone.utc),
        }
        self.historico.insert_one(resultado)
        return resultado
