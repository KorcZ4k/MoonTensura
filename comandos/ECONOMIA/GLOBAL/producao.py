from datetime import datetime, timezone
from pymongo import ReturnDocument


class MotorProducao:
    """Controla produção, fornecedores, insumos, logística e reposição de estoque."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.produtos = db["Economia_Produtos"]
        self.fornecedores = db["Economia_Fornecedores"]
        self.producao = db["Economia_Producao"]
        self.custos = db["Economia_Custos"]
        self.contratos = db["Economia_Contratos"]
        self.rotas = db["Economia_Rotas"]

    def configurar_fornecedor(self, fornecedor_id, nome, capacidade_por_ciclo=100, custo_base=1.0, ativo=True, insumos=None):
        self.fornecedores.update_one(
            {"fornecedor_id": str(fornecedor_id)},
            {"$set": {
                "fornecedor_id": str(fornecedor_id), "nome": nome,
                "capacidade_por_ciclo": max(0, int(capacidade_por_ciclo)),
                "capacidade_disponivel": max(0, int(capacidade_por_ciclo)),
                "custo_base": max(0.01, float(custo_base)),
                "ativo": bool(ativo), "insumos": insumos or [],
                "atualizado_em": datetime.now(timezone.utc)
            }}, upsert=True)

    def cadastrar_rota(self, origem, destino, distancia_km, risco=0.1, eficiencia=1.0, tarifa=0.0):
        self.rotas.update_one(
            {"origem": str(origem), "destino": str(destino)},
            {"$set": {
                "origem": str(origem), "destino": str(destino),
                "distancia_km": max(0.0, float(distancia_km)),
                "risco": max(0.0, min(1.0, float(risco))),
                "eficiencia": max(0.01, float(eficiencia)),
                "tarifa": max(0.0, float(tarifa)),
                "atualizado_em": datetime.now(timezone.utc)
            }}, upsert=True)

    def _fornecedores_produto(self, produto):
        ids = [str(i) for i in produto.get("fornecedores", [])]
        consulta = {"ativo": True}
        if ids:
            consulta["fornecedor_id"] = {"$in": ids}
        return list(self.fornecedores.find(consulta).sort("custo_base", 1))

    def _selecionar_fornecedor(self, produto, quantidade):
        fornecedores = self._fornecedores_produto(produto)
        for fornecedor in fornecedores:
            capacidade = int(fornecedor.get("capacidade_disponivel", fornecedor.get("capacidade_por_ciclo", 0)))
            if capacidade >= quantidade:
                return fornecedor
        return None

    def _custo_logistico(self, fornecedor, mercado, valor_carga):
        if not fornecedor or not mercado:
            return 0.0
        rota = self.rotas.find_one({"origem": str(fornecedor["fornecedor_id"]), "destino": str(mercado["channel_id"])})
        if not rota:
            return valor_carga * 0.10
        distancia = float(rota.get("distancia_km", 0))
        risco = float(rota.get("risco", 0.1))
        eficiencia = float(rota.get("eficiencia", 1.0))
        tarifa = float(rota.get("tarifa", 0.0))
        frete = valor_carga * (0.01 + distancia * 0.00005) / eficiencia
        seguro = valor_carga * risco * 0.03
        return frete + seguro + tarifa

    def custo_producao(self, produto, quantidade, mercado=None, fornecedor=None):
        quantidade = max(1, int(quantidade))
        custo_unitario = float(produto.get("custo_unitario", produto.get("preco_base_bronze", 1) * 0.55))
        if fornecedor:
            custo_unitario = max(custo_unitario, float(fornecedor.get("custo_base", 1.0)))
        estado = self.motor.relatorio_global()
        inflacao = float(estado.get("indice_precos", 100.0)) / 100.0
        salarios = custo_unitario * 0.15 * quantidade
        insumos = custo_unitario * 0.55 * quantidade
        energia = custo_unitario * 0.10 * quantidade
        depreciacao = custo_unitario * 0.05 * quantidade
        base_logistica = custo_unitario * 0.15 * quantidade
        if mercado and mercado.get("tipo") == "taverna":
            base_logistica *= 0.8
        logistica = base_logistica + self._custo_logistico(fornecedor, mercado, custo_unitario * quantidade)
        total = (salarios + insumos + energia + depreciacao + logistica) * inflacao
        return {"unitario": max(1.0, total / quantidade), "total": max(1.0, total),
                "salarios": salarios * inflacao, "insumos": insumos * inflacao,
                "energia": energia * inflacao, "depreciacao": depreciacao * inflacao,
                "logistica": logistica * inflacao}

    def repor_mercado(self, guild_id, channel_id, produto_id, quantidade=None):
        mercado = self.motor.mercado_do_canal(guild_id, channel_id)
        if not mercado: return {"erro": "mercado_nao_configurado"}
        produto = self.produtos.find_one({"produto_id": str(produto_id)})
        if not produto: return {"erro": "produto_nao_encontrado"}
        pid = str(produto_id)
        estoque_atual = int(mercado.get("estoque", {}).get(pid, 0))
        alvo = int(produto.get("estoque_padrao", 100))
        necessidade = max(0, alvo - estoque_atual)
        quantidade = necessidade if quantidade is None else min(necessidade, max(0, int(quantidade)))
        if quantidade <= 0: return {"erro": "estoque_adequado", "estoque": estoque_atual}

        fornecedor = self._selecionar_fornecedor(produto, quantidade)
        if produto.get("fornecedores") and not fornecedor:
            return {"erro": "fornecedor_sem_capacidade"}
        custo = self.custo_producao(produto, quantidade, mercado, fornecedor)

        resultado = self.motor.mercados.find_one_and_update(
            {"_id": mercado["_id"]},
            {"$inc": {f"estoque.{pid}": quantidade, "custos_operacionais_bronze": custo["total"],
                      "custo_salarios_bronze": custo["salarios"], "custo_insumos_bronze": custo["insumos"],
                      "custo_energia_bronze": custo["energia"], "custo_depreciacao_bronze": custo["depreciacao"],
                      "custo_logistica_bronze": custo["logistica"]},
             "$set": {"ultima_reposicao": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER)

        if fornecedor:
            self.fornecedores.update_one({"_id": fornecedor["_id"]}, {"$inc": {"capacidade_disponivel": -quantidade}})
        self.producao.insert_one({"guild_id": str(guild_id), "channel_id": str(channel_id), "produto_id": pid,
                                  "quantidade": quantidade, "fornecedor_id": fornecedor.get("fornecedor_id") if fornecedor else None,
                                  "custo_total_bronze": custo["total"], "criado_em": datetime.now(timezone.utc)})
        return {"mercado": resultado, "quantidade": quantidade, "custo": custo, "fornecedor": fornecedor}

    def restaurar_capacidades(self):
        self.fornecedores.update_many({"ativo": True}, [{"$set": {"capacidade_disponivel": "$capacidade_por_ciclo"}}])

    def ciclo_reposicao(self):
        resultados = []
        self.restaurar_capacidades()
        for mercado in self.motor.mercados.find():
            produtos_ids = set(mercado.get("estoque", {}).keys())
            for produto_id in produtos_ids:
                produto = self.produtos.find_one({"produto_id": str(produto_id)})
                if not produto: continue
                estoque = int(mercado.get("estoque", {}).get(produto_id, 0))
                alvo = int(produto.get("estoque_padrao", 100))
                if estoque >= max(1, int(alvo * 0.35)): continue
                resultado = self.repor_mercado(mercado["guild_id"], mercado["channel_id"], produto_id)
                if "erro" not in resultado: resultados.append(resultado)
        return resultados
