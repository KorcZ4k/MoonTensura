from datetime import datetime, timezone


class MotorEstabilizacaoGlobal:
    """Audita e estabiliza usando o esquema econômico oficial e compatibilidade legada."""

    LIMITES = {
        "prosperidade": (0.0, 100.0), "desenvolvimento": (0.0, 100.0), "estabilidade": (0.0, 100.0),
        "demanda": (0.0, 100.0), "capacidade_producao": (0.0, 1_000_000.0),
        "preco_medio": (0.01, 1_000_000_000.0), "capital": (0.0, 1_000_000_000_000.0),
        "caixa_bronze": (0.0, 1_000_000_000_000.0), "receita_bronze": (0.0, 1_000_000_000_000.0),
        "custos_bronze": (0.0, 1_000_000_000_000.0), "patrimonio_bronze": (0.0, 1_000_000_000_000.0),
    }

    def __init__(self, db, motor=None):
        self.db = db
        self.territorios = db["Economia_Territorios"]
        self.empresas = db["Economia_Empresas"]
        self.rotas = db["Economia_Rotas"]
        self.mercados = db["Mercados"]
        self.mercados_legados = db["Economia_Mercados"]
        self.eventos = db["Economia_Eventos"]

    @staticmethod
    def _numero(valor):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return None

    def _auditar_colecao(self, colecao, campos):
        documentos = correcoes = invalidos = 0
        for documento in colecao.find({}):
            documentos += 1; ajustes = {}
            for campo in campos:
                if campo not in documento: continue
                numero = self._numero(documento.get(campo)); minimo, maximo = self.LIMITES[campo]
                if numero is None:
                    ajustes[campo] = minimo; invalidos += 1; continue
                corrigido = min(maximo, max(minimo, numero))
                if corrigido != numero:
                    ajustes[campo] = corrigido; correcoes += 1
            if ajustes:
                ajustes["ultima_estabilizacao_em"] = datetime.now(timezone.utc)
                colecao.update_one({"_id": documento["_id"]}, {"$set": ajustes})
        return documentos, correcoes, invalidos

    def _rotas_invalidas(self):
        corrigidas = desativadas = 0
        for rota in self.rotas.find({}):
            ajustes = {}; origem = rota.get("origem") or rota.get("territorio_origem"); destino = rota.get("destino") or rota.get("territorio_destino")
            if origem and destino and str(origem) == str(destino):
                ajustes.update({"status": "suspensa", "motivo_suspensao": "origem_e_destino_iguais"}); desativadas += 1
            volume = self._numero(rota.get("volume"))
            if volume is not None and volume < 0: ajustes["volume"] = 0; corrigidas += 1
            if ajustes:
                ajustes["ultima_estabilizacao_em"] = datetime.now(timezone.utc)
                self.rotas.update_one({"_id": rota["_id"]}, {"$set": ajustes})
        return corrigidas, desativadas

    def executar_ciclo(self):
        territorios, ct, it = self._auditar_colecao(self.territorios, ("prosperidade", "desenvolvimento", "estabilidade"))
        empresas, ce, ie = self._auditar_colecao(self.empresas, ("caixa_bronze", "capital", "receita_bronze", "custos_bronze", "patrimonio_bronze", "capacidade_producao", "preco_medio"))
        mercados, cm, im = self._auditar_colecao(self.mercados, ("demanda", "preco_medio"))
        if mercados == 0:
            mercados, cm, im = self._auditar_colecao(self.mercados_legados, ("demanda", "preco_medio"))
        cr, suspensas = self._rotas_invalidas()
        resultado = {"territorios_auditados": territorios, "empresas_auditadas": empresas, "mercados_auditados": mercados, "correcoes_aplicadas": ct + ce + cm + cr, "valores_invalidos": it + ie + im, "rotas_suspensas": suspensas, "economia_estavel": (it + ie + im) == 0 and suspensas == 0}
        self.eventos.insert_one({"tipo": "auditoria_economia_global", "resultado": resultado, "criado_em": datetime.now(timezone.utc)})
        return resultado
