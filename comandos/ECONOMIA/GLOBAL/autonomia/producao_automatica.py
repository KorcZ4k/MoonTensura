from datetime import datetime, timezone


class MotorProducaoAutonoma:
    """Etapa 2: produção e estoque automáticos para empresas sem jogador."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.empresas = db["Economia_Empresas"]
        self.mercados = db["Mercados"]
        self.eventos = db["Economia_Eventos"]

    @staticmethod
    def _estoque_total(mercado):
        return sum(max(0.0, float(v)) for v in (mercado.get("estoque") or {}).values())

    def _capacidade_producao(self, empresa):
        capital = max(0.0, float(empresa.get("caixa_bronze", 0)))
        funcionarios = len(empresa.get("funcionarios") or [])
        tipo = str(empresa.get("tipo", "comercio")).lower()
        base = max(1, funcionarios * 5)
        if tipo in {"industria", "fabrica", "manufatura", "mineracao", "agricultura"}:
            base *= 2
        return max(1, min(500, int(base + capital / 10000)))

    def analisar_empresa(self, empresa):
        mercados = []
        for chave in empresa.get("mercados") or []:
            try:
                guild_id, channel_id = chave.split(":", 1)
            except ValueError:
                continue
            mercado = self.mercados.find_one({"guild_id": str(guild_id), "channel_id": str(channel_id)})
            if mercado:
                mercados.append(mercado)

        if not mercados:
            return {"acao": "aguardar", "motivo": "sem_mercado_vinculado", "mercados": []}

        demanda = sum(float(m.get("demanda", 0)) for m in mercados)
        oferta = sum(float(m.get("oferta", 0)) for m in mercados)
        estoque = sum(self._estoque_total(m) for m in mercados)
        capacidade = self._capacidade_producao(empresa)

        # Meta cresce quando a demanda supera a oferta e diminui quando há excesso.
        pressao = demanda - oferta
        meta = capacidade
        if pressao > 0:
            meta = min(capacidade, max(1, int(pressao)))
        elif estoque > capacidade * 3:
            meta = 0
        elif estoque > capacidade:
            meta = max(1, int(capacidade * 0.5))

        caixa = max(0.0, float(empresa.get("caixa_bronze", 0)))
        custo_unitario = max(1.0, float(empresa.get("custo_unitario_bronze", 10.0)))
        quantidade_financiavel = int(caixa // custo_unitario)
        quantidade = max(0, min(meta, quantidade_financiavel))

        if quantidade <= 0:
            return {
                "acao": "aguardar",
                "motivo": "caixa_insuficiente" if meta > 0 else "estoque_suficiente",
                "quantidade": 0,
                "custo_unitario": custo_unitario,
                "mercados": mercados,
            }

        return {
            "acao": "produzir",
            "quantidade": quantidade,
            "custo_unitario": custo_unitario,
            "custo_total": quantidade * custo_unitario,
            "mercados": mercados,
        }

    def executar_empresa(self, empresa):
        analise = self.analisar_empresa(empresa)
        agora = datetime.now(timezone.utc)

        if analise["acao"] != "produzir":
            self.empresas.update_one(
                {"_id": empresa["_id"]},
                {"$set": {
                    "autonomia.ultima_decisao": analise["motivo"],
                    "autonomia.ultimo_ciclo": agora,
                    "atualizada_em": agora,
                }}
            )
            return {"empresa_id": empresa["_id"], "produzido": 0, "acao": analise["acao"]}

        quantidade = analise["quantidade"]
        custo_total = analise["custo_total"]
        mercados = analise["mercados"]
        por_mercado = quantidade // len(mercados)
        resto = quantidade % len(mercados)

        for indice, mercado in enumerate(mercados):
            adicionar = por_mercado + (1 if indice < resto else 0)
            if adicionar <= 0:
                continue
            estoque = dict(mercado.get("estoque") or {})
            produto = str(empresa.get("produto_principal") or empresa.get("tipo") or "mercadoria")
            estoque[produto] = float(estoque.get(produto, 0)) + adicionar
            self.mercados.update_one(
                {"_id": mercado["_id"]},
                {"$set": {"estoque": estoque, "atualizado_em": agora}, "$inc": {"oferta": adicionar, "custos_operacionais_bronze": custo_total * (adicionar / quantidade)}}
            )

        self.empresas.update_one(
            {"_id": empresa["_id"]},
            {"$inc": {"caixa_bronze": -custo_total, "custos_bronze": custo_total}, "$set": {
                "autonomia.ultima_decisao": "producao_automatica",
                "autonomia.ultimo_ciclo": agora,
                "autonomia.ultima_producao": {"quantidade": quantidade, "custo_bronze": custo_total, "em": agora},
                "atualizada_em": agora,
            }}
        )

        return {"empresa_id": empresa["_id"], "produzido": quantidade, "custo_bronze": custo_total, "acao": "produzir"}

    def executar_ciclo(self):
        resultados = []
        for empresa in self.empresas.find({
            "status": "ativa",
            "autonomia.ativa": True,
            "gestao": {"$in": ["automatico", "estatal", "misto"]},
        }):
            resultados.append(self.executar_empresa(empresa))

        produzidas = sum(int(r.get("produzido", 0)) for r in resultados)
        ativas = sum(1 for r in resultados if r.get("acao") == "produzir")
        return {"empresas_processadas": len(resultados), "empresas_produzindo": ativas, "unidades_produzidas": produzidas, "resultados": resultados}
