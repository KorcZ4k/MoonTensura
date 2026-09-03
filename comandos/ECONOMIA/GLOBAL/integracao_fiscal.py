from datetime import datetime, timezone


class IntegradorFiscalMacroeconomico:
    """Conecta orçamento público aos agregados macroeconômicos."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.eventos = db["Economia_Eventos"]

    def aplicar(self, macro=None):
        from comandos.ECONOMIA.GLOBAL.politica_fiscal import MotorPoliticaFiscal

        macro = macro or {}
        resultados = MotorPoliticaFiscal(self.db, self.motor).processar_ciclo(macro)

        receita = sum(float(x.get("receita_bronze", 0.0)) for x in resultados)
        gasto = sum(float(x.get("gasto_bronze", 0.0)) for x in resultados)
        saldo = sum(float(x.get("saldo_fiscal_bronze", 0.0)) for x in resultados)
        divida = sum(float(x.get("divida_total_bronze", 0.0)) for x in resultados)
        deficit = sum(float(x.get("deficit_bronze", 0.0)) for x in resultados)

        demanda_privada = float(macro.get("demanda_agregada_bronze", 0.0))
        demanda_total = demanda_privada + gasto
        multiplicador = 1.0 + min(2.0, gasto / max(1.0, demanda_privada))
        pressao_fiscal = (gasto - receita) / max(1.0, demanda_total)

        estado = self.motor.relatorio_global()
        self.motor.economia.update_one(
            {"_id": "global"},
            {"$set": {
                "receita_publica_bronze": receita,
                "gasto_publico_bronze": gasto,
                "saldo_fiscal_global_bronze": saldo,
                "deficit_publico_bronze": deficit,
                "divida_publica_bronze": divida,
                "demanda_agregada_com_governo_bronze": demanda_total,
                "multiplicador_fiscal": multiplicador,
                "pressao_fiscal": pressao_fiscal,
                "ultimo_ciclo_fiscal": datetime.now(timezone.utc),
            }},
            upsert=True,
        )

        return {
            "governos_processados": len(resultados),
            "resultados": resultados,
            "receita_publica_bronze": receita,
            "gasto_publico_bronze": gasto,
            "saldo_fiscal_bronze": saldo,
            "deficit_bronze": deficit,
            "divida_publica_bronze": divida,
            "demanda_total_bronze": demanda_total,
            "multiplicador_fiscal": multiplicador,
            "pressao_fiscal": pressao_fiscal,
            "indice_precos_anterior": float(estado.get("indice_precos", 100.0)),
        }
