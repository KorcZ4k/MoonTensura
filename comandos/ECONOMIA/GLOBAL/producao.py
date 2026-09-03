from datetime import datetime, timezone
from pymongo import ReturnDocument


class MotorProducao:
    """Controla produção, fornecedores, custos e reposição real de estoque."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.produtos = db["Economia_Produtos"]
        self.fornecedores = db["Economia_Fornecedores"]
        self.producao = db["Economia_Producao"]
        self.custos = db["Economia_Custos"]

    def configurar_fornecedor(self, fornecedor_id, nome, capacidade_por_ciclo=100, custo_base=1.0, ativo=True):
        self.fornecedores.update_one(
            {"fornecedor_id": str(fornecedor_id)},
            {"$set": {
                "fornecedor_id": str(fornecedor_id),
                "nome": nome,
                "capacidade_por_ciclo": max(0, int(capacidade_por_ciclo)),
                "custo_base": max(0.01, float(custo_base)),
                "ativo": bool(ativo),
                "atualizado_em": datetime.now(timezone.utc)
            }},
            upsert=True
        )

    def custo_producao(self, produto, quantidade, mercado=None):
        quantidade = max(1, int(quantidade))
        custo_unitario = float(produto.get("custo_unitario", produto.get("preco_base_bronze", 1) * 0.55))
        estado = self.motor.relatorio_global()
        inflacao = float(estado.get("indice_precos", 100.0)) / 100.0
        salarios = custo_unitario * 0.15
        insumos = custo_unitario * 0.55
        energia = custo_unitario * 0.10
        depreciacao = custo_unitario * 0.05
        logistica = custo_unitario * 0.15
        if mercado and mercado.get("tipo") == "taverna":
            logistica *= 0.8
        custo = (salarios + insumos + energia + depreciacao + logistica) * inflacao
        return {
            "unitario": max(1.0, custo),
            "total": max(1.0, custo * quantidade),
            "salarios": salarios * quantidade,
            "insumos": insumos * quantidade,
            "energia": energia * quantidade,
            "depreciacao": depreciacao * quantidade,
            "logistica": logistica * quantidade,
        }

    def repor_mercado(self, guild_id, channel_id, produto_id, quantidade=None):
        mercado = self.motor.mercado_do_canal(guild_id, channel_id)
        if not mercado:
            return {"erro": "mercado_nao_configurado"}

        produto = self.produtos.find_one({"produto_id": str(produto_id)})
        if not produto:
            return {"erro": "produto_nao_encontrado"}

        pid = str(produto_id)
        estoque_atual = int(mercado.get("estoque", {}).get(pid, 0))
        alvo = int(produto.get("estoque_padrao", 100))
        necessidade = max(0, alvo - estoque_atual)
        quantidade = necessidade if quantidade is None else min(necessidade, max(0, int(quantidade)))
        if quantidade <= 0:
            return {"erro": "estoque_adequado", "estoque": estoque_atual}

        custo = self.custo_producao(produto, quantidade, mercado)
        resultado = self.motor.mercados.find_one_and_update(
            {"_id": mercado["_id"]},
            {"$inc": {
                f"estoque.{pid}": quantidade,
                "custos_operacionais_bronze": custo["total"],
                "custo_salarios_bronze": custo["salarios"],
                "custo_insumos_bronze": custo["insumos"],
                "custo_energia_bronze": custo["energia"],
                "custo_depreciacao_bronze": custo["depreciacao"],
                "custo_logistica_bronze": custo["logistica"],
            }, "$set": {"ultima_reposicao": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER
        )

        self.producao.insert_one({
            "guild_id": str(guild_id), "channel_id": str(channel_id),
            "produto_id": pid, "quantidade": quantidade,
            "custo_total_bronze": custo["total"], "criado_em": datetime.now(timezone.utc)
        })
        return {"mercado": resultado, "quantidade": quantidade, "custo": custo}

    def ciclo_reposicao(self):
        resultados = []
        for mercado in self.motor.mercados.find():
            for produto_id, estoque in mercado.get("estoque", {}).items():
                produto = self.produtos.find_one({"produto_id": str(produto_id)})
                if not produto:
                    continue
                alvo = int(produto.get("estoque_padrao", 100))
                if int(estoque) >= max(1, int(alvo * 0.35)):
                    continue
                resultado = self.repor_mercado(mercado["guild_id"], mercado["channel_id"], produto_id)
                if "erro" not in resultado:
                    resultados.append(resultado)
        return resultados
