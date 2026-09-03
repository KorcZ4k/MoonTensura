from datetime import datetime, timezone


class OrquestradorEconomiaGlobal:
    """Executa o ciclo econômico e isola falhas individuais dos módulos."""

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
        modulos = [
            ("controlador_autonomia", "comandos.ECONOMIA.GLOBAL.autonomia.controlador", "ControladorAutonomiaEmpresas", "executar_ciclo_base"),
            ("producao_autonoma", "comandos.ECONOMIA.GLOBAL.autonomia.producao_automatica", "MotorProducaoAutonoma", "executar_ciclo"),
            ("mercado_autonomo", "comandos.ECONOMIA.GLOBAL.autonomia.mercado_autonomo", "MotorMercadoAutonomo", "executar_ciclo"),
            ("rotas_automaticas", "comandos.ECONOMIA.GLOBAL.autonomia.rotas_automaticas", "MotorRotasAutomaticas", "executar_ciclo"),
            ("populacao_npc", "comandos.ECONOMIA.GLOBAL.autonomia.populacao_npc", "MotorPopulacaoNPC", "executar_ciclo"),
            ("ciclo_empresarial", "comandos.ECONOMIA.GLOBAL.autonomia.ciclo_empresarial", "MotorCicloEmpresarial", "executar_ciclo"),
            ("sistema_financeiro", "comandos.ECONOMIA.GLOBAL.autonomia.sistema_financeiro", "MotorFinanceiroAutonomo", "executar_ciclo"),
            ("crises_dinamicas", "comandos.ECONOMIA.GLOBAL.autonomia.crises_dinamicas", "MotorCrisesDinamicas", "executar_ciclo"),
            ("comercio_territorial", "comandos.ECONOMIA.GLOBAL.autonomia.comercio_territorial", "MotorComercioTerritorial", "executar_ciclo"),
            ("governo_e_tesouro", "comandos.ECONOMIA.GLOBAL.autonomia.governo_e_tesouro", "MotorGovernoETesouro", "executar_ciclo"),
            ("governo_autonomo", "comandos.ECONOMIA.GLOBAL.autonomia.governo_autonomo", "MotorGovernoAutonomo", "executar_ciclo"),
            ("recursos_naturais", "comandos.ECONOMIA.GLOBAL.autonomia.recursos_naturais", "MotorRecursosNaturais", "executar_ciclo"),
            ("guerra_e_economia", "comandos.ECONOMIA.GLOBAL.autonomia.guerra_e_economia", "MotorGuerraEEconomia", "executar_ciclo"),
            ("diplomacia_economica", "comandos.ECONOMIA.GLOBAL.autonomia.diplomacia_economica", "MotorDiplomaciaEconomica", "executar_ciclo"),
            ("evolucao_territorial", "comandos.ECONOMIA.GLOBAL.autonomia.evolucao_territorial", "MotorEvolucaoTerritorial", "executar_ciclo"),
            ("circulacao_monetaria", "comandos.ECONOMIA.GLOBAL.autonomia.circulacao_monetaria", "MotorCirculacaoMonetaria", "executar_ciclo"),
            ("empresas_npc_avancadas", "comandos.ECONOMIA.GLOBAL.autonomia.empresas_npc_avancadas", "MotorEmpresasNPCAvancadas", "executar_ciclo"),
            ("eventos_economicos_mundiais", "comandos.ECONOMIA.GLOBAL.autonomia.eventos_economicos_mundiais", "MotorEventosEconomicosMundiais", "executar_ciclo"),
            ("estabilizacao_global", "comandos.ECONOMIA.GLOBAL.autonomia.estabilizacao_global", "MotorEstabilizacaoGlobal", "executar_ciclo"),
        ]
        for nome, caminho, classe_nome, metodo_nome in modulos:
            modulo = __import__(caminho, fromlist=[classe_nome])
            classe = getattr(modulo, classe_nome)
            resultado[nome] = self._seguro(nome, lambda c=classe, m=metodo_nome: getattr(c(self.db, self.motor), m)(), {})

        from comandos.ECONOMIA.GLOBAL.recuperacao import MotorRecuperacaoEconomica
        resultado["recuperacao"] = self._seguro("recuperacao", lambda: MotorRecuperacaoEconomica(self.db, self.motor).processar_ciclo(), {})
        from comandos.ECONOMIA.GLOBAL.validacao import ValidadorEconomia
        resultado["validacao"] = self._seguro("validacao", lambda: ValidadorEconomia(self.db, self.motor).executar(), {})
        from comandos.ECONOMIA.GLOBAL.relatorios import MotorRelatoriosEconomicos
        resultado["relatorio"] = self._seguro("relatorios", lambda: MotorRelatoriosEconomicos(self.db, self.motor).gerar_global(), {})
        resultado["executado_em"] = datetime.now(timezone.utc)
        resultado["ciclo_completo"] = True
        return resultado
