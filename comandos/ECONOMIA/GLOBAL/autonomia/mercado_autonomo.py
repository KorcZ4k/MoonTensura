from datetime import datetime, timezone


class MotorMercadoAutonomo:
    """Etapa 3: ajusta preços e pressão de mercado de forma automática."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.mercados = db["Mercados"]
        self.empresas = db["Economia_Empresas"]
        self.eventos = db["Economia_Acontecimentos"]

    @staticmethod
    def _numero(valor, padrao=0.0):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(padrao)

    def _oferta(self, mercado):
        estoque = mercado.get("estoque") or {}
        estoque_total = sum(max(0.0, self._numero(v)) for v in estoque.values()) if isinstance(estoque, dict) else 0.0
        return max(self._numero(mercado.get("oferta")), estoque_total)

    def analisar(self, mercado):
        demanda = max(0.0, self._numero(mercado.get("demanda")))
        oferta = max(0.0, self._oferta(mercado))
        preco_atual = max(0.01, self._numero(mercado.get("indice_preco", mercado.get("preco_medio", 100.0)), 100.0))

        if demanda <= 0 and oferta <= 0:
            return {"acao": "manter", "fator": 1.0, "motivo": "sem_dados"}

        # Relação limitada para impedir oscilações absurdas em um único ciclo.
        pressao = (demanda + 1.0) / (oferta + 1.0)
        if pressao >= 1.50:
            fator = min(1.10, 1.0 + (pressao - 1.0) * 0.08)
            acao = "aumentar"
            motivo = "demanda_superior_oferta"
        elif pressao <= 0.67:
            fator = max(0.90, 1.0 - (1.0 - pressao) * 0.08)
            acao = "reduzir"
            motivo = "excesso_oferta"
        else:
            fator = 1.0
            acao = "manter"
            motivo = "equilibrio"

        return {
            "acao": acao,
            "fator": fator,
            "motivo": motivo,
            "demanda": demanda,
            "oferta": oferta,
            "preco_anterior": preco_atual,
            "preco_novo": round(preco_atual * fator, 4),
        }

    def executar_mercado(self, mercado):
        analise = self.analisar(mercado)
        agora = datetime.now(timezone.utc)

        self.mercados.update_one(
            {"_id": mercado["_id"]},
            {"$set": {
                "indice_preco": analise.get("preco_novo", analise.get("preco_anterior", 100.0)),
                "pressao_mercado": analise.get("demanda", 0.0) / max(1.0, analise.get("oferta", 0.0)),
                "mercado_autonomo.ultima_acao": analise["acao"],
                "mercado_autonomo.motivo": analise["motivo"],
                "mercado_autonomo.ultimo_ciclo": agora,
                "atualizado_em": agora,
            }}
        )

        if analise["acao"] != "manter":
            self.eventos.insert_one({
                "guild_id": str(mercado.get("guild_id", "global")),
                "tipo": "empresas",
                "titulo": "Mercado ajustou seus preços automaticamente",
                "descricao": (
                    f"O mercado {mercado.get('nome', mercado.get('channel_id', 'desconhecido'))} "
                    f"decidiu {analise['acao']} os preços devido a {analise['motivo']}. "
                    f"Índice: {analise['preco_anterior']:.2f} → {analise['preco_novo']:.2f}."
                ),
                "dados": analise,
                "prioridade": "normal",
                "criado_em": agora,
                "publicado": False,
            })

        return analise

    def executar_ciclo(self):
        resultados = []
        for mercado in self.mercados.find({}):
            resultados.append(self.executar_mercado(mercado))

        return {
            "mercados_processados": len(resultados),
            "precos_aumentados": sum(1 for r in resultados if r["acao"] == "aumentar"),
            "precos_reduzidos": sum(1 for r in resultados if r["acao"] == "reduzir"),
            "precos_estaveis": sum(1 for r in resultados if r["acao"] == "manter"),
        }
