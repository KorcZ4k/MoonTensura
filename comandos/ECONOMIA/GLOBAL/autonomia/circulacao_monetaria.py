from datetime import datetime, timezone

from comandos.ECONOMIA.GLOBAL.sistema_monetario import SistemaMonetarioHunos


class MotorCirculacaoMonetaria:
    """Normaliza os valores financeiros usando Bronze como unidade interna oficial."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.empresas = db["Economia_Empresas"]
        self.governos = db["Economia_Governos"]

    def _normalizar_colecao(self, colecao, campos, nome_saida):
        processados = total = 0
        for documento in colecao.find({}):
            campo_origem = next((campo for campo in campos if documento.get(campo) is not None), campos[0])
            valor = SistemaMonetarioHunos.normalizar_saldo(documento, campo_origem)
            valor = max(0, int(valor))
            colecao.update_one({"_id": documento["_id"]}, {"$set": {
                f"{nome_saida}_bronze": valor,
                f"{nome_saida}_moedas": SistemaMonetarioHunos.decompor(valor),
                f"{nome_saida}_formatado": SistemaMonetarioHunos.formatar(valor),
                "moeda_padrao": "hunos",
                "unidade_base_monetaria": "bronze",
                "atualizado_monetario_em": datetime.now(timezone.utc),
            }})
            processados += 1
            total += valor
        return processados, total

    def executar_ciclo(self):
        empresas, capital = self._normalizar_colecao(self.empresas, ("caixa_bronze", "capital_bronze", "capital", "saldo_bronze", "saldo"), "capital")
        governos, tesouro = self._normalizar_colecao(self.governos, ("tesouro_bronze", "tesouro", "saldo_bronze", "saldo"), "tesouro")
        return {"empresas_normalizadas": empresas, "capital_em_bronze": capital, "governos_normalizados": governos, "tesouro_em_bronze": tesouro}
