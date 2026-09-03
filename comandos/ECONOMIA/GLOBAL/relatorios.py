from datetime import datetime, timezone


class MotorRelatoriosEconomicos:
    """Consolida indicadores macro e microeconômicos em relatórios auditáveis."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.relatorios = db["Economia_Relatorios"]
        self.empresas = db["Economia_Empresas"]
        self.mercados = db["Mercados"]
        self.populacao = db["Economia_Populacao"]
        self.empregos = db["Economia_Empregos"]
        self.crises = db["Economia_Crises"]

    @staticmethod
    def _numero(valor):
        try:
            return float(valor or 0)
        except (TypeError, ValueError):
            return 0.0

    def gerar_global(self):
        estado = self.motor.relatorio_global()
        empresas = list(self.empresas.find())
        mercados = list(self.mercados.find())
        populacoes = list(self.populacao.find())

        receita = sum(self._numero(e.get("receita_bronze", e.get("receita"))) for e in empresas)
        custos = sum(self._numero(e.get("custos_operacionais_bronze", e.get("custos"))) for e in empresas)
        caixa = sum(self._numero(e.get("caixa_bronze", e.get("caixa"))) for e in empresas)
        divida = sum(self._numero(e.get("divida_bronze", e.get("divida"))) for e in empresas)
        falidas = sum(1 for e in empresas if e.get("status") == "falida")
        empregados = self.empregos.count_documents({"status": "ativo"})
        vagas = self.empregos.count_documents({"status": "vaga"})
        pea = sum(self._numero(p.get("populacao_economicamente_ativa", p.get("pea", p.get("populacao")))) for p in populacoes)
        desempregados = max(0.0, pea - empregados)
        taxa_desemprego = desempregados / max(1.0, pea)

        crises_ativas = list(self.crises.find({"status": "ativa"}))
        lucro = receita - custos
        margem = lucro / max(1.0, receita)

        relatorio = {
            "data": datetime.now(timezone.utc),
            "tipo": "global",
            "macro": {
                "indice_precos": self._numero(estado.get("indice_precos", 100)),
                "inflacao_minuto": self._numero(estado.get("inflacao_minuto")),
                "taxa_juros": self._numero(estado.get("taxa_juros")),
                "demanda_agregada": self._numero(estado.get("demanda_agregada")),
                "oferta_agregada": self._numero(estado.get("oferta_agregada")),
                "confianca_economica": self._numero(estado.get("confianca_economica", 50)),
                "credito_disponivel_bronze": self._numero(estado.get("credito_disponivel_bronze")),
                "reservas_monetarias_bronze": self._numero(estado.get("reservas_monetarias_bronze")),
                "fluxo_capital_bronze": self._numero(estado.get("fluxo_capital")),
            },
            "trabalho": {
                "empregados": empregados,
                "vagas_abertas": vagas,
                "desempregados_estimados": desempregados,
                "taxa_desemprego": taxa_desemprego,
                "populacao_economicamente_ativa": pea,
            },
            "empresas": {
                "total": len(empresas),
                "falidas": falidas,
                "ativas": len(empresas) - falidas,
                "receita_bronze": receita,
                "custos_bronze": custos,
                "lucro_bronze": lucro,
                "margem_liquida": margem,
                "caixa_bronze": caixa,
                "divida_bronze": divida,
            },
            "mercados": {
                "total": len(mercados),
                "receita_bronze": sum(self._numero(m.get("receita_bronze")) for m in mercados),
                "vendas": sum(int(self._numero(m.get("vendas_total"))) for m in mercados),
            },
            "crises": {
                "ativas": len(crises_ativas),
                "tipos": [c.get("tipo") for c in crises_ativas],
            },
        }
        relatorio["classificacao"] = self.classificar(relatorio)
        self.relatorios.insert_one(relatorio)
        return relatorio

    def classificar(self, relatorio):
        macro = relatorio["macro"]
        trabalho = relatorio["trabalho"]
        empresas = relatorio["empresas"]

        pontos = 50.0
        pontos += max(-20, min(20, (macro["confianca_economica"] - 50) * 0.4))
        pontos -= min(25, trabalho["taxa_desemprego"] * 100 * 0.5)
        pontos += max(-15, min(15, empresas["margem_liquida"] * 50))
        pontos -= min(15, abs(macro["inflacao_minuto"]) * 10000)

        if pontos >= 70:
            estado = "expansao"
        elif pontos >= 55:
            estado = "estavel"
        elif pontos >= 40:
            estado = "desaceleracao"
        elif pontos >= 25:
            estado = "recessao"
        else:
            estado = "crise"

        return {"indice_saude": max(0.0, min(100.0, pontos)), "estado": estado}

    def ultimo_global(self):
        return self.relatorios.find_one({"tipo": "global"}, sort=[("data", -1)])
