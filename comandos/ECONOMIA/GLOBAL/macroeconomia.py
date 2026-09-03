from datetime import datetime, timezone


class MotorMacroeconomia:
    """Conecta população, trabalho, empresas, produção e mercados ao ciclo macroeconômico."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.populacoes = db["Economia_Populacao"]
        self.empregos = db["Economia_Empregos"]
        self.empresas = db["Economia_Empresas"]
        self.producao = db["Economia_Producao"]
        self.historico = db["Economia_Macro_Historico"]

    def calcular(self):
        populacoes = list(self.populacoes.find())
        empresas = list(self.empresas.find({"status": {"$in": ["ativa", "insolvente"]}}))
        mercados = list(self.motor.mercados.find())
        empregos = list(self.empregos.find())

        populacao_total = sum(int(p.get("quantidade", 0)) for p in populacoes)
        empregados = sum(int(p.get("empregados", 0)) for p in populacoes)
        desempregados = sum(int(p.get("desempregados", 0)) for p in populacoes)
        renda_nominal = sum(float(p.get("renda_mensal_total_bronze", 0)) * (int(p.get("empregados", 0)) / max(1, int(p.get("quantidade", 1)))) for p in populacoes)
        renda_real = sum(float(self.motor.relatorio_global().get("indice_precos", 100.0)) > 0 and float(p.get("renda_mensal_total_bronze", 0)) * (int(p.get("empregados", 0)) / max(1, int(p.get("quantidade", 1)))) / (float(self.motor.relatorio_global().get("indice_precos", 100.0)) / 100.0) for p in populacoes)

        massa_salarial = sum(float(e.get("salario_bronze", e.get("salario", 0))) * int(e.get("contratados", e.get("ocupadas", 0))) for e in empregos)
        receita_empresas = sum(float(e.get("receita_bronze", 0)) for e in empresas)
        custos_empresas = sum(float(e.get("custos_bronze", 0)) for e in empresas)
        producao_total = sum(float(x.get("quantidade_produzida", x.get("producao", x.get("quantidade", 0)))) for x in self.producao.find())

        demanda_agregada = renda_real * 0.72
        consumo_observado = sum(float(m.get("receita_bronze", 0)) for m in mercados)
        oferta_mercado = sum(float(m.get("oferta", 0)) + sum(float(v) for v in m.get("estoque", {}).values()) for m in mercados) + producao_total
        if oferta_mercado <= 0:
            oferta_mercado = 1.0
        hiato = (demanda_agregada - oferta_mercado) / max(demanda_agregada, oferta_mercado, 1.0)
        taxa_desemprego = desempregados / max(1, populacao_total)
        utilizacao = min(1.5, demanda_agregada / max(oferta_mercado, 1.0))

        resultado = {
            "data": datetime.now(timezone.utc),
            "populacao_total": populacao_total,
            "empregados": empregados,
            "desempregados": desempregados,
            "taxa_desemprego": taxa_desemprego,
            "renda_nominal_bronze": renda_nominal,
            "renda_real_bronze": renda_real,
            "massa_salarial_bronze": massa_salarial,
            "demanda_agregada_bronze": demanda_agregada,
            "consumo_observado_bronze": consumo_observado,
            "oferta_agregada": oferta_mercado,
            "producao_total": producao_total,
            "hiato_oferta_demanda": hiato,
            "utilizacao_capacidade": utilizacao,
            "receita_empresas_bronze": receita_empresas,
            "custos_empresas_bronze": custos_empresas,
        }
        self.historico.insert_one(resultado)
        return resultado

    def aplicar(self):
        macro = self.calcular()
        hiato = float(macro["hiato_oferta_demanda"])
        desemprego = float(macro["taxa_desemprego"])
        pressao = hiato * 0.35 - desemprego * 0.05
        pressao = max(-0.008, min(0.008, pressao))
        atual = self.motor.relatorio_global()
        indice = max(1.0, float(atual.get("indice_precos", 100.0)) * (1.0 + pressao))
        politica = "pressao_inflacionaria" if pressao > 0.0005 else "pressao_deflacionaria" if pressao < -0.0005 else "estavel"
        self.motor.economia.update_one({"_id": "global"}, {"$set": {
            "indice_precos": indice,
            "pressao_macro": pressao,
            "demanda_agregada": macro["demanda_agregada_bronze"],
            "oferta_agregada": macro["oferta_agregada"],
            "taxa_desemprego_global": desemprego,
            "massa_salarial_bronze": macro["massa_salarial_bronze"],
            "renda_real_global_bronze": macro["renda_real_bronze"],
            "politica_ciclo": politica,
            "ultimo_ciclo_macro": datetime.now(timezone.utc)
        }}, upsert=True)
        macro["indice_precos"] = indice
        macro["pressao_macro"] = pressao
        macro["situacao"] = politica
        return macro
