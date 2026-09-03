import importlib
import inspect
from datetime import datetime, timezone


class DiagnosticoEconomiaGlobal:
    """Auditoria estrutural dos módulos chamados pelo ciclo econômico automático."""

    MODULOS = (
        ("eventos", "comandos.ECONOMIA.GLOBAL.eventos", "MotorEventosEconomicos", "processar_eventos"),
        ("producao", "comandos.ECONOMIA.GLOBAL.producao", "MotorProducao", "ciclo_reposicao"),
        ("empresas", "comandos.ECONOMIA.GLOBAL.empresas", "MotorEmpresas", "sincronizar_mercados"),
        ("banco", "comandos.ECONOMIA.GLOBAL.banco", "MotorFinanceiro", "processar_vencimentos"),
        ("financeiro_avancado", "comandos.ECONOMIA.GLOBAL.financeiro_avancado", "MotorFinanceiroAvancado", "processar_ciclo"),
        ("credito", "comandos.ECONOMIA.GLOBAL.credito", "MotorCredito", "processar_ciclo"),
        ("populacao", "comandos.ECONOMIA.GLOBAL.populacao", "MotorPopulacao", "ciclo_consumo"),
        ("macroeconomia", "comandos.ECONOMIA.GLOBAL.macroeconomia", "MotorMacroeconomia", "aplicar"),
        ("trabalho", "comandos.ECONOMIA.GLOBAL.integracao_trabalho", "IntegradorMercadoTrabalho", "processar_ciclo"),
        ("fiscal", "comandos.ECONOMIA.GLOBAL.integracao_fiscal", "IntegradorFiscalMacroeconomico", "aplicar"),
        ("politica_monetaria", "comandos.ECONOMIA.GLOBAL.politica_monetaria", "MotorPoliticaMonetaria", "processar_ciclo"),
        ("investimentos", "comandos.ECONOMIA.GLOBAL.investimentos", "MotorInvestimentos", "processar_ciclo"),
        ("crises", "comandos.ECONOMIA.GLOBAL.crises", "MotorCrisesEconomicas", "processar_ciclo"),
        ("indicadores", "comandos.ECONOMIA.GLOBAL.indicadores", "MotorIndicadoresEconomicos", "aplicar"),
        ("recuperacao", "comandos.ECONOMIA.GLOBAL.recuperacao", "MotorRecuperacaoEconomica", "processar_ciclo"),
        ("validacao", "comandos.ECONOMIA.GLOBAL.validacao", "ValidadorEconomia", "executar"),
        ("relatorios", "comandos.ECONOMIA.GLOBAL.relatorios", "MotorRelatoriosEconomicos", "gerar_global"),
    )

    def __init__(self, db):
        self.db = db
        self.historico = db["Economia_Diagnosticos"]

    @staticmethod
    def _assinatura(funcao):
        try:
            return str(inspect.signature(funcao))
        except (TypeError, ValueError):
            return "indisponivel"

    def executar(self):
        itens = []
        for nome, caminho, classe_nome, metodo_nome in self.MODULOS:
            item = {
                "nome": nome,
                "modulo": caminho,
                "classe": classe_nome,
                "metodo": metodo_nome,
                "status": "ok",
                "erro": None,
            }
            try:
                modulo = importlib.import_module(caminho)
                classe = getattr(modulo, classe_nome)
                metodo = getattr(classe, metodo_nome)
                item["assinatura"] = self._assinatura(metodo)
                item["classe_callable"] = callable(classe)
                item["metodo_callable"] = callable(metodo)
                if not item["classe_callable"] or not item["metodo_callable"]:
                    raise TypeError("Classe ou método não é executável")
            except Exception as erro:
                item["status"] = "erro"
                item["erro"] = f"{type(erro).__name__}: {erro}"
            itens.append(item)

        erros = [item for item in itens if item["status"] == "erro"]
        resultado = {
            "executado_em": datetime.now(timezone.utc),
            "total": len(itens),
            "ok": len(itens) - len(erros),
            "erros": len(erros),
            "saude_percentual": round(((len(itens) - len(erros)) / max(1, len(itens))) * 100, 2),
            "itens": itens,
        }
        self.historico.insert_one(resultado)
        return resultado
