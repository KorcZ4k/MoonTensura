from datetime import datetime, timezone


class MotorEstabilizacaoGlobal:
    """Etapa 18: auditoria e estabilização automática da economia global."""

    LIMITES = {
        "prosperidade": (0.0, 100.0),
        "desenvolvimento": (0.0, 100.0),
        "estabilidade": (0.0, 100.0),
        "demanda": (0.0, 100.0),
        "capacidade_producao": (0.0, 1_000_000.0),
        "preco_medio": (0.01, 1_000_000_000.0),
        "capital": (0.0, 1_000_000_000_000.0),
    }

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.territorios = db["Economia_Territorios"]
        self.empresas = db["Economia_Empresas"]
        self.rotas = db["Economia_Rotas"]
        self.mercados = db["Economia_Mercados"]
        self.eventos = db["Economia_Eventos"]

    @staticmethod
    def _numero(valor):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return None

    def _auditar_colecao(self, colecao, campos):
        documentos = 0
        correcoes = 0
        invalidos = 0

        for documento in colecao.find({}):
            documentos += 1
            ajustes = {}
            for campo in campos:
                if campo not in documento:
                    continue
                numero = self._numero(documento.get(campo))
                minimo, maximo = self.LIMITES[campo]
                if numero is None:
                    ajustes[campo] = minimo
                    invalidos += 1
                    continue
                corrigido = min(maximo, max(minimo, numero))
                if corrigido != numero:
                    ajustes[campo] = corrigido
                    correcoes += 1

            if ajustes:
                ajustes["ultima_estabilizacao_em"] = datetime.now(timezone.utc)
                colecao.update_one({"_id": documento["_id"]}, {"$set": ajustes})

        return documentos, correcoes, invalidos

    def _rotas_invalidas(self):
        corrigidas = 0
        desativadas = 0
        for rota in self.rotas.find({}):
            ajustes = {}
            origem = rota.get("origem") or rota.get("territorio_origem")
            destino = rota.get("destino") or rota.get("territorio_destino")

            if origem and destino and str(origem) == str(destino):
                ajustes["status"] = "suspensa"
                ajustes["motivo_suspensao"] = "origem_e_destino_iguais"
                desativadas += 1

            volume = self._numero(rota.get("volume"))
            if volume is not None and volume < 0:
                ajustes["volume"] = 0
                corrigidas += 1

            if ajustes:
                ajustes["ultima_estabilizacao_em"] = datetime.now(timezone.utc)
                self.rotas.update_one({"_id": rota["_id"]}, {"$set": ajustes})
        return corrigidas, desativadas

    def executar_ciclo(self):
        territorios, c_territorios, i_territorios = self._auditar_colecao(
            self.territorios, ("prosperidade", "desenvolvimento", "estabilidade")
        )
        empresas, c_empresas, i_empresas = self._auditar_colecao(
            self.empresas, ("capital", "capacidade_producao", "preco_medio")
        )
        mercados, c_mercados, i_mercados = self._auditar_colecao(
            self.mercados, ("demanda", "preco_medio")
        )
        c_rotas, rotas_suspensas = self._rotas_invalidas()

        total_correcoes = c_territorios + c_empresas + c_mercados + c_rotas
        total_invalidos = i_territorios + i_empresas + i_mercados

        resultado = {
            "territorios_auditados": territorios,
            "empresas_auditadas": empresas,
            "mercados_auditados": mercados,
            "correcoes_aplicadas": total_correcoes,
            "valores_invalidos": total_invalidos,
            "rotas_suspensas": rotas_suspensas,
            "economia_estavel": total_invalidos == 0 and rotas_suspensas == 0,
        }

        self.eventos.insert_one({
            "tipo": "auditoria_economia_global",
            "resultado": resultado,
            "criado_em": datetime.now(timezone.utc),
        })
        return resultado
