from datetime import datetime, timezone


class MotorComercioTerritorial:
    """Etapa 9: comércio entre regiões, reinos e nações."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.rotas = db["Economia_Rotas"]
        self.mercados = db["Mercados"]
        self.tratados = db["Economia_Tratados"]
        self.acontecimentos = db["Economia_Acontecimentos"]

    @staticmethod
    def _numero(valor):
        try:
            return max(0.0, float(valor or 0))
        except (TypeError, ValueError):
            return 0.0

    def _territorio(self, documento):
        return {
            "regiao": documento.get("regiao") or documento.get("regiao_id"),
            "reino": documento.get("reino") or documento.get("reino_id"),
            "pais": documento.get("pais") or documento.get("pais_id") or documento.get("nacao"),
        }

    def _registrar(self, guild_id, tipo, titulo, descricao, dados, prioridade="normal"):
        self.acontecimentos.insert_one({
            "guild_id": str(guild_id), "tipo": tipo,
            "titulo": titulo, "descricao": descricao,
            "dados": dados, "prioridade": prioridade,
            "criado_em": datetime.now(timezone.utc), "publicado": False,
        })

    def _tratado_ativo(self, guild_id, origem, destino):
        consulta = {
            "guild_id": str(guild_id),
            "status": "ativo",
            "$or": [
                {"origem": origem.get("pais"), "destino": destino.get("pais")},
                {"origem": destino.get("pais"), "destino": origem.get("pais")},
            ],
        }
        return self.tratados.find_one(consulta)

    def processar_rota(self, rota):
        if rota.get("status", "ativa") not in {"ativa", "pendente"}:
            return {"acao": "ignorada"}

        origem = self.mercados.find_one({"_id": rota.get("mercado_origem_id")})
        destino = self.mercados.find_one({"_id": rota.get("mercado_destino_id")})
        if not origem or not destino:
            return {"acao": "sem_mercado"}

        territorio_origem = self._territorio(origem)
        territorio_destino = self._territorio(destino)
        internacional = bool(territorio_origem.get("pais") and territorio_destino.get("pais") and territorio_origem["pais"] != territorio_destino["pais"])
        inter_reino = bool(territorio_origem.get("reino") and territorio_destino.get("reino") and territorio_origem["reino"] != territorio_destino["reino"])
        tratado = self._tratado_ativo(rota.get("guild_id"), territorio_origem, territorio_destino) if internacional else None

        tarifa = 0.0
        if internacional:
            tarifa = 0.08
        elif inter_reino:
            tarifa = 0.04
        if tratado:
            tarifa *= 0.5

        valor = self._numero(rota.get("lucro_estimado_bronze") or rota.get("valor_estimado_bronze"))
        tarifa_valor = valor * tarifa
        agora = datetime.now(timezone.utc)
        campos = {
            "territorio_origem": territorio_origem,
            "territorio_destino": territorio_destino,
            "tipo_comercio": "internacional" if internacional else ("inter_reino" if inter_reino else "regional"),
            "tarifa_percentual": tarifa,
            "tarifa_estimada_bronze": tarifa_valor,
            "tratado_aplicado": bool(tratado),
            "ultima_analise_territorial": agora,
        }
        self.rotas.update_one({"_id": rota["_id"]}, {"$set": campos})

        if internacional and not rota.get("anuncio_territorial_realizado"):
            self.rotas.update_one({"_id": rota["_id"]}, {"$set": {"anuncio_territorial_realizado": True}})
            self._registrar(
                rota.get("guild_id"), "rotas_comerciais",
                "🌐 Nova rota internacional",
                "Uma rota comercial passou a conectar territórios de diferentes nações.",
                {"rota_id": str(rota["_id"]), "origem": territorio_origem, "destino": territorio_destino, "tarifa": tarifa},
            )

        return {"acao": campos["tipo_comercio"], "tarifa": tarifa_valor, "tratado": bool(tratado)}

    def executar_ciclo(self):
        resultados = [self.processar_rota(rota) for rota in self.rotas.find({})]
        return {
            "rotas_processadas": len(resultados),
            "comercio_internacional": sum(1 for r in resultados if r.get("acao") == "internacional"),
            "comercio_inter_reino": sum(1 for r in resultados if r.get("acao") == "inter_reino"),
            "tarifas_estimadas_bronze": sum(self._numero(r.get("tarifa")) for r in resultados),
            "tratados_aplicados": sum(1 for r in resultados if r.get("tratado")),
        }
