from datetime import datetime, timezone


class PublicadorLogsEconomicos:
    """Centraliza acontecimentos econômicos para canais de log configurados."""

    TIPOS = {
        "rota": "rotas_comerciais",
        "tratado": "tratados_empresariais",
        "anuncio": "anuncios_governamentais",
        "crise": "crises_financeiras",
        "empresa": "empresas",
    }

    def __init__(self, db):
        self.db = db
        self.config = db["Economia_Canais_Logs"]
        self.fila = db["Economia_Acontecimentos"]

    def registrar_canais(self, guild_id, canais):
        """canais: {rotas_comerciais: channel_id, ...}"""
        documento = {
            "guild_id": str(guild_id),
            "canais": {k: str(v) for k, v in canais.items() if k in self.TIPOS.values() and v},
            "atualizado_em": datetime.now(timezone.utc),
        }
        self.config.update_one({"guild_id": str(guild_id)}, {"$set": documento}, upsert=True)
        return documento

    def registrar(self, guild_id, tipo, titulo, descricao, dados=None, prioridade="normal"):
        categoria = self.TIPOS.get(tipo, tipo)
        documento = {
            "guild_id": str(guild_id),
            "tipo": categoria,
            "titulo": str(titulo),
            "descricao": str(descricao),
            "dados": dados or {},
            "prioridade": prioridade,
            "criado_em": datetime.now(timezone.utc),
            "publicado": False,
        }
        resultado = self.fila.insert_one(documento)
        documento["_id"] = resultado.inserted_id
        return documento

    async def publicar_pendentes(self, bot, limite=25):
        publicados = 0
        pendentes = self.fila.find({"publicado": False}).sort("criado_em", 1).limit(limite)
        for evento in pendentes:
            config = self.config.find_one({"guild_id": evento["guild_id"]}) or {}
            canal_id = (config.get("canais") or {}).get(evento["tipo"])
            if not canal_id:
                continue
            canal = bot.get_channel(int(canal_id))
            if canal is None:
                try:
                    canal = await bot.fetch_channel(int(canal_id))
                except Exception:
                    continue
            try:
                await canal.send(embed=self._criar_embed(evento))
                self.fila.update_one({"_id": evento["_id"]}, {"$set": {"publicado": True, "publicado_em": datetime.now(timezone.utc)}})
                publicados += 1
            except Exception as erro:
                self.fila.update_one({"_id": evento["_id"]}, {"$set": {"ultimo_erro": str(erro)}})
        return publicados

    @staticmethod
    def _criar_embed(evento):
        import discord
        cores = {
            "rotas_comerciais": discord.Color.blue(),
            "tratados_empresariais": discord.Color.purple(),
            "anuncios_governamentais": discord.Color.gold(),
            "crises_financeiras": discord.Color.red(),
            "empresas": discord.Color.green(),
        }
        embed = discord.Embed(
            title=evento["titulo"],
            description=evento["descricao"],
            color=cores.get(evento["tipo"], discord.Color.blurple()),
            timestamp=evento["criado_em"],
        )
        embed.set_footer(text="Economia Global • Moon Tensura")
        return embed
