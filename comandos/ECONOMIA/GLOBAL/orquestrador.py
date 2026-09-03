from datetime import datetime, timezone


class OrquestradorEconomiaGlobal:
    """Executa o ciclo-base e a etapa final de recuperação, auditoria e relatório."""

    def __init__(self, motor):
        self.motor = motor
        self.db = motor.db
        self.eventos = self.db["Economia_Eventos"]

    def _seguro(self, nome, funcao, padrao=None):
        try:
            return funcao()
        except Exception as erro:
            self.eventos.insert_one({
                "tipo": "erro_orquestrador",
                "modulo": nome,
                "erro": str(erro),
                "criado_em": datetime.now(timezone.utc),
            })
            return {"erro": str(erro)} if padrao is None else padrao

    def executar_ciclo_completo(self):
        resultado = self._seguro("ciclo_base", self.motor.ciclo_economico, {})

        from comandos.ECONOMIA.GLOBAL.recuperacao import MotorRecuperacaoEconomica
        resultado["recuperacao"] = self._seguro(
            "recuperacao",
            lambda: MotorRecuperacaoEconomica(self.db, self.motor).processar_ciclo(),
            {},
        )

        from comandos.ECONOMIA.GLOBAL.validacao import ValidadorEconomia
        resultado["validacao"] = self._seguro(
            "validacao",
            lambda: ValidadorEconomia(self.db, self.motor).executar(),
            {},
        )

        from comandos.ECONOMIA.GLOBAL.relatorios import MotorRelatoriosEconomicos
        resultado["relatorio"] = self._seguro(
            "relatorios",
            lambda: MotorRelatoriosEconomicos(self.db, self.motor).gerar_global(),
            {},
        )

        resultado["executado_em"] = datetime.now(timezone.utc)
        resultado["ciclo_completo"] = True
        return resultado
