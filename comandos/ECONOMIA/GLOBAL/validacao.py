from datetime import datetime, timezone


class ValidadorEconomia:
    """Audita o estado econômico e corrige apenas inconsistências matemáticas seguras."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.auditorias = db["Economia_Auditorias"]
        self.mercados = db["Mercados"]
        self.empresas = db["Economia_Empresas"]

    @staticmethod
    def _numero(valor, padrao=0.0):
        try:
            return float(valor if valor is not None else padrao)
        except (TypeError, ValueError):
            return float(padrao)

    def validar_global(self):
        estado = self.motor.relatorio_global()
        problemas = []
        correcoes = {}

        for campo in ("indice_precos", "taxa_juros", "confianca_economica", "credito_disponivel_bronze", "reservas_monetarias_bronze"):
            valor = self._numero(estado.get(campo))
            if valor < 0:
                problemas.append({"campo": campo, "problema": "valor_negativo", "valor": valor})
                correcoes[campo] = 0.0

        if self._numero(estado.get("indice_precos", 100)) < 1:
            correcoes["indice_precos"] = 1.0

        confianca = self._numero(estado.get("confianca_economica", 50))
        if confianca > 100:
            correcoes["confianca_economica"] = 100.0
            problemas.append({"campo": "confianca_economica", "problema": "acima_do_limite", "valor": confianca})

        if correcoes:
            self.motor.economia.update_one({"_id": "global"}, {"$set": correcoes})

        return problemas, correcoes

    def validar_mercados(self):
        problemas = []
        corrigidos = 0
        for mercado in self.mercados.find():
            estoque = mercado.get("estoque", {})
            if not isinstance(estoque, dict):
                self.mercados.update_one({"_id": mercado["_id"]}, {"$set": {"estoque": {}}})
                problemas.append({"mercado": str(mercado["_id"]), "problema": "estoque_invalido"})
                corrigidos += 1
                continue

            novo_estoque = {}
            alterado = False
            for item, quantidade in estoque.items():
                valor = max(0.0, self._numero(quantidade))
                novo_estoque[str(item)] = valor
                alterado = alterado or valor != quantidade

            if alterado:
                self.mercados.update_one({"_id": mercado["_id"]}, {"$set": {"estoque": novo_estoque}})
                corrigidos += 1

        return problemas, corrigidos

    def validar_empresas(self):
        problemas = []
        corrigidos = 0
        for empresa in self.empresas.find():
            alteracoes = {}
            for campo in ("receita_bronze", "custos_operacionais_bronze", "caixa_bronze", "divida_bronze"):
                if campo in empresa and self._numero(empresa.get(campo)) < 0 and campo != "divida_bronze":
                    alteracoes[campo] = 0.0
                    problemas.append({"empresa": str(empresa["_id"]), "campo": campo, "problema": "valor_negativo"})
            if alteracoes:
                self.empresas.update_one({"_id": empresa["_id"]}, {"$set": alteracoes})
                corrigidos += 1
        return problemas, corrigidos

    def executar(self):
        problemas_global, correcoes_global = self.validar_global()
        problemas_mercados, mercados_corrigidos = self.validar_mercados()
        problemas_empresas, empresas_corrigidas = self.validar_empresas()

        resultado = {
            "data": datetime.now(timezone.utc),
            "global": {
                "problemas": problemas_global,
                "correcoes": correcoes_global,
            },
            "mercados": {
                "problemas": problemas_mercados,
                "corrigidos": mercados_corrigidos,
            },
            "empresas": {
                "problemas": problemas_empresas,
                "corrigidos": empresas_corrigidas,
            },
            "total_problemas": len(problemas_global) + len(problemas_mercados) + len(problemas_empresas),
        }
        self.auditorias.insert_one(resultado)
        return resultado
