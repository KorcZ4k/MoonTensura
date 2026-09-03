from datetime import datetime, timezone

CATEGORIAS_POR_MERCADO = {
    "taverna": {"comida", "bebida", "hospedagem", "cura", "consumivel"},
    "loja": {"item", "equipamento", "consumivel", "arma", "armadura", "utilidade", "cura", "atributo", "sorte", "experiencia"},
    "bazar": {"roupa", "vestuario", "acessorio", "tecido", "skin"},
}

class MercadoEconomico:
    def __init__(self, motor):
        self.motor = motor
        self.db = motor.db
        self.produtos = self.db["Economia_Produtos"]
        self.transacoes = self.db["Economia_Transacoes"]

    def categoria_permitida(self, mercado, categoria):
        return str(categoria or "item").lower() in CATEGORIAS_POR_MERCADO.get(mercado.get("tipo"), set())

    def normalizar_produto(self, item):
        categoria = str(item.get("categoria") or item.get("tipo") or "item").lower()
        return {
            "produto_id": str(item.get("id") or item.get("produto_id")),
            "nome": item.get("nome", "Produto"),
            "preco_base_bronze": max(1, float(item.get("preco", item.get("preco_base_bronze", 1)))),
            "categoria": categoria,
            "estoque_padrao": int(item.get("estoque", item.get("estoque_padrao", 100))),
        }

    def registrar_produto(self, produto_id, nome, preco_base_bronze, categoria, estoque=100, custo_unitario=None):
        self.produtos.update_one({"produto_id": str(produto_id)}, {"$set": {
            "produto_id": str(produto_id), "nome": nome,
            "preco_base_bronze": max(1, float(preco_base_bronze)), "categoria": str(categoria).lower(),
            "estoque_padrao": max(0, int(estoque)),
            "custo_unitario": float(custo_unitario if custo_unitario is not None else preco_base_bronze * 0.55),
            "atualizado_em": datetime.now(timezone.utc)
        }}, upsert=True)

    def garantir_estoque(self, guild_id, channel_id, produto):
        mercado = self.motor.mercado_do_canal(guild_id, channel_id)
        if not mercado: return None
        pid = str(produto["produto_id"])
        if pid not in mercado.get("estoque", {}):
            self.motor.mercados.update_one({"_id": mercado["_id"]}, {"$set": {f"estoque.{pid}": int(produto.get("estoque_padrao", 100))}})
            mercado = self.motor.mercado_do_canal(guild_id, channel_id)
        return mercado

    def cotar(self, guild_id, channel_id, produto, quantidade=1):
        mercado = self.garantir_estoque(guild_id, channel_id, produto)
        if not mercado: return {"erro": "mercado_nao_configurado"}
        if not self.categoria_permitida(mercado, produto.get("categoria")):
            return {"erro": "categoria_invalida", "mercado": mercado}
        quantidade = max(1, int(quantidade)); estoque = int(mercado.get("estoque", {}).get(str(produto["produto_id"]), 0))
        if estoque < quantidade: return {"erro": "estoque_insuficiente", "estoque": estoque, "mercado": mercado}
        preco = self.motor.preco_dinamico(produto["preco_base_bronze"], guild_id, channel_id)
        escassez = 1 + max(0, (50 - estoque) / 200)
        preco = max(1, int(round(preco * escassez)))
        return {"preco_unitario": preco, "preco_total": preco * quantidade, "estoque": estoque, "mercado": mercado}

    def comprar(self, guild_id, channel_id, user_id, produto, quantidade=1):
        cotacao = self.cotar(guild_id, channel_id, produto, quantidade)
        if "erro" in cotacao: return cotacao
        quantidade = max(1, int(quantidade)); pid = str(produto["produto_id"]); mercado = cotacao["mercado"]
        resultado = self.motor.mercados.update_one({"_id": mercado["_id"], f"estoque.{pid}": {"$gte": quantidade}}, {"$inc": {f"estoque.{pid}": -quantidade, "receita_bronze": cotacao["preco_total"], "vendas_total": quantidade}})
        if resultado.modified_count == 0: return {"erro": "estoque_insuficiente"}
        self.motor.registrar_transacao(guild_id, channel_id, cotacao["preco_total"], quantidade, "compra")
        self.transacoes.insert_one({"guild_id": str(guild_id), "channel_id": str(channel_id), "user_id": str(user_id), "produto_id": pid, "quantidade": quantidade, "valor_bronze": cotacao["preco_total"], "tipo": "compra", "criado_em": datetime.now(timezone.utc)})
        return cotacao
