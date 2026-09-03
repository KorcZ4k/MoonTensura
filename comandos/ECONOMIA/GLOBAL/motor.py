import math
import random
from datetime import datetime, timezone
from pymongo import ReturnDocument

BRONZE_USD = 1
PRATA_BRONZE = 100
OURO_PRATA = 100
OURO_ESTELAR_OURO = 100


class MotorEconomiaGlobal:
    """Motor persistente de macro e microeconomia baseado na coleção Economia."""

    def __init__(self, db):
        self.db = db
        self.economia = db["Economia"]
        self.mercados = db["Mercados"]
        self.eventos = db["Economia_Eventos"]
        self._inicializar()

    def _inicializar(self):
        self.economia.update_one(
            {"_id": "global"},
            {"$setOnInsert": {
                "_id": "global",
                "indice_precos": 100.0,
                "inflacao_minuto": 0.0,
                "liquidez_ouro": 100000.0,
                "fluxo_capital": 0.0,
                "balanca_comercial": {},
                "taxa_juros": 0.05,
                "politica_monetaria": "estavel",
                "ultimo_tick": datetime.now(timezone.utc),
                "versao": 1
            }},
            upsert=True
        )

    @staticmethod
    def converter_bronze(valor_bronze: float):
        valor = max(0, int(round(valor_bronze)))
        ouro_estelar, resto = divmod(valor, 1_000_000)
        ouro, resto = divmod(resto, 10_000)
        prata, bronze = divmod(resto, 100)
        return {
            "ouro_estelar": ouro_estelar,
            "ouro": ouro,
            "prata": prata,
            "bronze": bronze,
            "bronze_total": valor,
            "usd_paridade": valor * BRONZE_USD
        }

    @staticmethod
    def formatar_moeda(valor_bronze: float):
        c = MotorEconomiaGlobal.converter_bronze(valor_bronze)
        partes = []
        if c["ouro_estelar"]: partes.append(f"{c['ouro_estelar']} Ouro Estelar")
        if c["ouro"]: partes.append(f"{c['ouro']} Ouro")
        if c["prata"]: partes.append(f"{c['prata']} Prata")
        if c["bronze"] or not partes: partes.append(f"{c['bronze']} Bronze")
        return " | ".join(partes)

    def configurar_mercado(self, guild_id, channel_id, tipo, categoria="comum"):
        tipo = tipo.lower()
        if tipo not in {"taverna", "loja", "bazar"}:
            raise ValueError("Tipo inválido")
        if tipo == "taverna" and categoria not in {"comum", "imperial"}:
            raise ValueError("Categoria de taverna inválida")
        self.mercados.update_one(
            {"guild_id": str(guild_id), "channel_id": str(channel_id)},
            {"$set": {
                "guild_id": str(guild_id), "channel_id": str(channel_id),
                "tipo": tipo, "categoria": categoria,
                "estoque_total": 1000, "demanda": 0.0,
                "oferta": 0.0, "volume_minuto": 0.0,
                "multiplicador_preco": 1.0,
                "criado_em": datetime.now(timezone.utc)
            }}, upsert=True)

    def mercado_do_canal(self, guild_id, channel_id):
        return self.mercados.find_one({"guild_id": str(guild_id), "channel_id": str(channel_id)})

    def registrar_transacao(self, guild_id, channel_id, valor_bronze, quantidade=1, lado="compra"):
        mercado = self.mercado_do_canal(guild_id, channel_id)
        if not mercado:
            return None
        quantidade = max(1, int(quantidade))
        demanda = quantidade if lado == "compra" else 0
        oferta = quantidade if lado == "venda" else 0
        novo = self.mercados.find_one_and_update(
            {"_id": mercado["_id"]},
            {"$inc": {
                "demanda": demanda,
                "oferta": oferta,
                "volume_minuto": abs(float(valor_bronze))
            }, "$set": {"ultima_transacao": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER)
        self.economia.update_one(
            {"_id": "global"},
            {"$inc": {"fluxo_capital": abs(float(valor_bronze))}}, upsert=True)
        return novo

    def preco_dinamico(self, preco_base_bronze, guild_id, channel_id):
        mercado = self.mercado_do_canal(guild_id, channel_id)
        global_doc = self.economia.find_one({"_id": "global"}) or {}
        if not mercado:
            return max(1, int(round(preco_base_bronze)))
        demanda = float(mercado.get("demanda", 0))
        oferta = float(mercado.get("oferta", 0))
        pressao = (demanda - oferta) / max(10.0, demanda + oferta + 10.0)
        local = 1.0 + max(-0.45, min(1.50, pressao * 2.0))
        inflacao = float(global_doc.get("indice_precos", 100.0)) / 100.0
        multiplicador = local * inflacao
        self.mercados.update_one({"_id": mercado["_id"]}, {"$set": {"multiplicador_preco": multiplicador}})
        return max(1, int(round(float(preco_base_bronze) * multiplicador)))

    def tick(self):
        """Um minuto econômico: inflação responde à pressão agregada e ruído de mercado."""
        mercados = list(self.mercados.find())
        demanda = sum(float(m.get("demanda", 0)) for m in mercados)
        oferta = sum(float(m.get("oferta", 0)) for m in mercados)
        volume = sum(float(m.get("volume_minuto", 0)) for m in mercados)
        pressao = (demanda - oferta) / max(100.0, demanda + oferta + 100.0)
        choque = random.uniform(-0.00035, 0.00035)
        delta = max(-0.01, min(0.01, pressao * 0.004 + choque))
        novo = self.economia.find_one_and_update(
            {"_id": "global"},
            {"$inc": {"indice_precos": float(self.economia.find_one({"_id":"global"}).get("indice_precos",100.0) * delta)},
             "$set": {"inflacao_minuto": delta, "ultimo_tick": datetime.now(timezone.utc),
                      "demanda_agregada": demanda, "oferta_agregada": oferta, "volume_mercado": volume}},
            return_document=ReturnDocument.AFTER)
        for mercado in mercados:
            self.mercados.update_one({"_id": mercado["_id"]}, {"$set": {"demanda": 0.0, "oferta": 0.0, "volume_minuto": 0.0}})
        return novo

    def relatorio_global(self):
        return self.economia.find_one({"_id": "global"}) or {}
