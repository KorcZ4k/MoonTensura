from datetime import datetime, timezone


class MotorRotasAutomaticas:
    """Etapa 4: identifica escassez e excesso e cria oportunidades comerciais."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.mercados = db["Mercados"]
        self.rotas = db["Economia_Rotas"]
        self.empresas = db["Economia_Empresas"]
        self.acontecimentos = db["Economia_Acontecimentos"]

    @staticmethod
    def _preco(mercado, produto):
        precos = mercado.get("precos") or mercado.get("precos_bronze") or {}
        return max(0.0, float(precos.get(produto, 0)))

    @staticmethod
    def _estoque(mercado, produto):
        return max(0.0, float((mercado.get("estoque") or {}).get(produto, 0)))

    def _registrar(self, guild_id, titulo, descricao, dados):
        self.acontecimentos.insert_one({
            "guild_id": str(guild_id),
            "tipo": "rotas_comerciais",
            "titulo": titulo,
            "descricao": descricao,
            "dados": dados,
            "prioridade": "normal",
            "criado_em": datetime.now(timezone.utc),
            "publicado": False,
        })

    def _produtos(self, mercado):
        return set((mercado.get("estoque") or {}).keys()) | set((mercado.get("precos") or {}).keys())

    def _candidatas(self, origem, destino):
        produtos = self._produtos(origem) & self._produtos(destino)
        resultados = []
        for produto in produtos:
            preco_origem = self._preco(origem, produto)
            preco_destino = self._preco(destino, produto)
            estoque_origem = self._estoque(origem, produto)
            estoque_destino = self._estoque(destino, produto)
            demanda_destino = max(0.0, float(destino.get("demanda", 0)))

            if preco_origem <= 0 or preco_destino <= preco_origem:
                continue
            if estoque_origem <= max(5, demanda_destino * 0.1):
                continue

            quantidade = int(min(estoque_origem * 0.15, max(1, demanda_destino * 0.1), 1000))
            if quantidade <= 0:
                continue

            valor_compra = preco_origem * quantidade
            receita = preco_destino * quantidade
            frete = valor_compra * 0.05
            tarifas = receita * float(destino.get("tarifa_importacao", 0)) / 100
            lucro = receita - valor_compra - frete - tarifas

            if lucro > 0:
                resultados.append({
                    "produto": produto,
                    "quantidade": quantidade,
                    "valor_compra_bronze": valor_compra,
                    "receita_estimada_bronze": receita,
                    "frete_bronze": frete,
                    "tarifas_bronze": tarifas,
                    "lucro_estimado_bronze": lucro,
                })
        return resultados

    def executar_ciclo(self):
        mercados = list(self.mercados.find({}))
        oportunidades = 0
        rotas_criadas = 0

        for origem in mercados:
            for destino in mercados:
                if origem.get("_id") == destino.get("_id"):
                    continue
                if str(origem.get("guild_id")) != str(destino.get("guild_id")):
                    continue

                for carga in self._candidatas(origem, destino):
                    oportunidades += 1
                    chave = {
                        "guild_id": str(origem.get("guild_id")),
                        "origem": str(origem.get("channel_id")),
                        "destino": str(destino.get("channel_id")),
                        "produto": carga["produto"],
                    }
                    existente = self.rotas.find_one(chave)
                    agora = datetime.now(timezone.utc)

                    if existente:
                        self.rotas.update_one({"_id": existente["_id"]}, {"$set": {"ultima_analise": agora, "carga_estimada": carga, "ativa": True}})
                        continue

                    documento = {
                        **chave,
                        "modelo": "automatica",
                        "ativa": True,
                        "criada_automaticamente": True,
                        "criada_em": agora,
                        "ultima_analise": agora,
                        "carga_estimada": carga,
                    }
                    self.rotas.insert_one(documento)
                    rotas_criadas += 1
                    self._registrar(
                        origem.get("guild_id"),
                        "💰 Nova oportunidade comercial",
                        f"Uma rota automática foi identificada para {carga['produto']} entre dois mercados.",
                        documento,
                    )

        return {
            "mercados_processados": len(mercados),
            "oportunidades_identificadas": oportunidades,
            "rotas_criadas": rotas_criadas,
        }
