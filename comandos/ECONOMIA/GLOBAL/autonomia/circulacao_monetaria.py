from datetime import datetime, timezone

from comandos.ECONOMIA.GLOBAL.sistema_monetario import SistemaMonetarioHunos


class MotorCirculacaoMonetaria:
    """Integra a moeda Hunos aos registros econômicos existentes."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.empresas = db["Economia_Empresas"]
        self.governos = db["Economia_Governos"]
        self.eventos = db["Economia_Eventos"]

    def _normalizar_colecao(self, colecao, campo):
        processados = 0
        total = 0
        for documento in colecao.find({}):
            valor = SistemaMonetarioHunos.normalizar_saldo(documento, campo)
            decomposicao = SistemaMonetarioHunos.decompor(valor)
            colecao.update_one(
                {"_id": documento["_id"]},
                {"$set": {
                    f"{campo}_bronze": int(valor),
                    f"{campo}_moedas": decomposicao,
                    f"{campo}_formatado": SistemaMonetarioHunos.formatar(valor),
                    "moeda_padrao": "hunos",
                    "atualizado_monetario_em": datetime.now(timezone.utc),
                }},
            )
            processados += 1
            total += int(valor)
        return processados, total

    def executar_ciclo(self):
        empresas, capital = self._normalizar_colecao(self.empresas, "capital")
        governos, tesouro = self._normalizar_colecao(self.governos, "tesouro")
        return {
            "empresas_normalizadas": empresas,
            "capital_em_bronze": capital,
            "governos_normalizados": governos,
            "tesouro_em_bronze": tesouro,
        }
