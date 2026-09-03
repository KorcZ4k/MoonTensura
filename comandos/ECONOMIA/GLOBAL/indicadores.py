from datetime import datetime, timezone


class MotorIndicadoresEconomicos:
    """Calcula indicadores macroeconômicos a partir dos dados persistidos da simulação."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.historico = db["Economia_Indicadores_Historico"]
        self.empresas = db["Economia_Empresas"]
        self.populacoes = db["Economia_Populacao"]

    def calcular(self, macro=None):
        estado = self.motor.relatorio_global() or {}
        if macro is None:
            macro = {}

        empresas = list(self.empresas.find({"status": {"$in": ["ativa", "insolvente"]}}))
        populacao_total = int(macro.get("populacao_total", 0))
        if populacao_total <= 0:
            populacao_total = sum(int(p.get("quantidade", 0)) for p in self.populacoes.find())

        receita = float(macro.get("receita_empresas_bronze", 0))
        custos = float(macro.get("custos_empresas_bronze", 0))
        consumo = float(macro.get("consumo_observado_bronze", 0))
        producao = float(macro.get("producao_total", 0))
        demanda = float(macro.get("demanda_agregada_bronze", 0))
        oferta = float(macro.get("oferta_agregada", 0))

        # PIB nominal aproximado pela produção e circulação efetiva da economia.
        pib_nominal = max(0.0, receita + consumo + max(0.0, producao))
        indice_precos = max(1.0, float(estado.get("indice_precos", 100.0)))
        pib_real = pib_nominal / (indice_precos / 100.0)
        pib_per_capita = pib_nominal / max(1, populacao_total)

        anterior = self.historico.find_one(sort=[("data", -1)])
        pib_anterior = float((anterior or {}).get("pib_nominal_bronze", 0))
        crescimento = ((pib_nominal - pib_anterior) / pib_anterior) if pib_anterior > 0 else 0.0

        inflacao = float(estado.get("inflacao_minuto", 0))
        desemprego = float(macro.get("taxa_desemprego", estado.get("taxa_desemprego_global", 0)))
        margem_empresarial = (receita - custos) / max(receita, 1.0)
        utilizacao = float(macro.get("utilizacao_capacidade", 0))
        saldo_oferta = oferta - demanda
        empresas_ativas = sum(1 for e in empresas if e.get("status") == "ativa")
        empresas_insolventes = sum(1 for e in empresas if e.get("status") == "insolvente")

        if crescimento > 0.01 and desemprego < 0.08:
            ciclo = "expansao"
        elif crescimento < -0.01 and desemprego > 0.10:
            ciclo = "recessao"
        elif crescimento < 0 and desemprego > 0.15:
            ciclo = "depressao"
        elif crescimento > 0.03 and inflacao > 0.003:
            ciclo = "superaquecimento"
        else:
            ciclo = "estabilizacao"

        resultado = {
            "data": datetime.now(timezone.utc),
            "pib_nominal_bronze": pib_nominal,
            "pib_real_bronze": pib_real,
            "pib_per_capita_bronze": pib_per_capita,
            "crescimento": crescimento,
            "inflacao": inflacao,
            "taxa_desemprego": desemprego,
            "demanda_agregada_bronze": demanda,
            "oferta_agregada": oferta,
            "saldo_oferta_demanda": saldo_oferta,
            "utilizacao_capacidade": utilizacao,
            "margem_empresarial": margem_empresarial,
            "empresas_ativas": empresas_ativas,
            "empresas_insolventes": empresas_insolventes,
            "ciclo_economico": ciclo,
            "indice_precos": indice_precos,
        }
        self.historico.insert_one(resultado)
        return resultado

    def aplicar(self, macro=None):
        indicadores = self.calcular(macro)
        self.motor.economia.update_one(
            {"_id": "global"},
            {"$set": {
                "pib_nominal_bronze": indicadores["pib_nominal_bronze"],
                "pib_real_bronze": indicadores["pib_real_bronze"],
                "pib_per_capita_bronze": indicadores["pib_per_capita_bronze"],
                "crescimento_economico": indicadores["crescimento"],
                "ciclo_economico": indicadores["ciclo_economico"],
                "margem_empresarial_media": indicadores["margem_empresarial"],
                "empresas_ativas": indicadores["empresas_ativas"],
                "empresas_insolventes": indicadores["empresas_insolventes"],
                "ultimo_calculo_indicadores": indicadores["data"],
            }},
            upsert=True,
        )
        return indicadores
