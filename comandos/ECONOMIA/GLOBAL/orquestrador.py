from datetime import datetime, timezone


class OrquestradorEconomiaGlobal:
    """Executa o ciclo-base e os módulos complementares da economia global."""

    def __init__(self, motor):
        self.motor = motor
        self.db = motor.db
        self.eventos = self.db["Economia_Eventos"]

    def _seguro(self, nome, funcao, padrao=None):
        try:
            return funcao()
        except Exception as erro:
            self.eventos.insert_one({"tipo": "erro_orquestrador", "modulo": nome, "erro": str(erro), "criado_em": datetime.now(timezone.utc)})
            return {"erro": str(erro)} if padrao is None else padrao

    def executar_ciclo_completo(self):
        resultado = self._seguro("ciclo_base", self.motor.ciclo_economico, {})

        from comandos.ECONOMIA.GLOBAL.autonomia.producao_automatica import MotorProducaoAutonoma
        resultado["producao_autonoma"] = self._seguro("producao_autonoma", lambda: MotorProducaoAutonoma(self.db, self.motor).executar_ciclo(), {})
        from comandos.ECONOMIA.GLOBAL.autonomia.mercado_autonomo import MotorMercadoAutonomo
        resultado["mercado_autonomo"] = self._seguro("mercado_autonomo", lambda: MotorMercadoAutonomo(self.db, self.motor).executar_ciclo(), {})
        from comandos.ECONOMIA.GLOBAL.autonomia.rotas_automaticas import MotorRotasAutomaticas
        resultado["rotas_automaticas"] = self._seguro("rotas_automaticas", lambda: MotorRotasAutomaticas(self.db, self.motor).executar_ciclo(), {})
        from comandos.ECONOMIA.GLOBAL.autonomia.populacao_npc import MotorPopulacaoNPC
        resultado["populacao_npc"] = self._seguro("populacao_npc", lambda: MotorPopulacaoNPC(self.db, self.motor).executar_ciclo(), {})
        from comandos.ECONOMIA.GLOBAL.autonomia.ciclo_empresarial import MotorCicloEmpresarial
        resultado["ciclo_empresarial"] = self._seguro("ciclo_empresarial", lambda: MotorCicloEmpresarial(self.db, self.motor).executar_ciclo(), {})
        from comandos.ECONOMIA.GLOBAL.autonomia.sistema_financeiro import MotorFinanceiroAutonomo
        resultado["sistema_financeiro"] = self._seguro("sistema_financeiro", lambda: MotorFinanceiroAutonomo(self.db, self.motor).executar_ciclo(), {})
        from comandos.ECONOMIA.GLOBAL.autonomia.crises_dinamicas import MotorCrisesDinamicas
        resultado["crises_dinamicas"] = self._seguro("crises_dinamicas", lambda: MotorCrisesDinamicas(self.db, self.motor).executar_ciclo(), {})
        from comandos.ECONOMIA.GLOBAL.autonomia.comercio_territorial import MotorComercioTerritorial
        resultado["comercio_territorial"] = self._seguro("comercio_territorial", lambda: MotorComercioTerritorial(self.db, self.motor).executar_ciclo(), {})
        from comandos.ECONOMIA.GLOBAL.autonomia.governo_e_tesouro import MotorGovernoETesouro
        resultado["governo_e_tesouro"] = self._seguro("governo_e_tesouro", lambda: MotorGovernoETesouro(self.db, self.motor).executar_ciclo(), {})
        from comandos.ECONOMIA.GLOBAL.autonomia.recursos_naturais import MotorRecursosNaturais
        resultado["recursos_naturais"] = self._seguro("recursos_naturais", lambda: MotorRecursosNaturais(self.db, self.motor).executar_ciclo(), {"recursos_processados": 0, "unidades_extraidas": 0, "recursos_esgotados": 0, "recursos_em_escassez": 0})

        # ETAPA 12 — conflitos, guerra e consequências econômicas.
        from comandos.ECONOMIA.GLOBAL.autonomia.guerra_e_economia import MotorGuerraEEconomia
        resultado["guerra_e_economia"] = self._seguro("guerra_e_economia", lambda: MotorGuerraEEconomia(self.db, self.motor).executar_ciclo(), {"conflitos_processados": 0, "empresas_afetadas": 0, "rotas_interrompidas": 0, "recursos_perdidos": 0})

        from comandos.ECONOMIA.GLOBAL.recuperacao import MotorRecuperacaoEconomica
        resultado["recuperacao"] = self._seguro("recuperacao", lambda: MotorRecuperacaoEconomica(self.db, self.motor).processar_ciclo(), {})
        from comandos.ECONOMIA.GLOBAL.validacao import ValidadorEconomia
        resultado["validacao"] = self._seguro("validacao", lambda: ValidadorEconomia(self.db, self.motor).executar(), {})
        from comandos.ECONOMIA.GLOBAL.relatorios import MotorRelatoriosEconomicos
        resultado["relatorio"] = self._seguro("relatorios", lambda: MotorRelatoriosEconomicos(self.db, self.motor).gerar_global(), {})

        resultado["executado_em"] = datetime.now(timezone.utc)
        resultado["ciclo_completo"] = True
        return resultado
