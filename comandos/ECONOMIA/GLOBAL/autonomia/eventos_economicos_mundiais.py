import random
from datetime import datetime, timezone


class MotorEventosEconomicosMundiais:
    """Etapa 17: acontecimentos econômicos autônomos que afetam o mundo."""

    TIPOS = (
        "descoberta_recurso",
        "oportunidade_comercial",
        "crescimento_regional",
        "escassez_regional",
        "desastre_natural",
        "crise_local",
        "boom_demografico",
    )

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.territorios = db["Economia_Territorios"]
        self.empresas = db["Economia_Empresas"]
        self.rotas = db["Economia_Rotas"]
        self.acontecimentos = db["Economia_Acontecimentos"]
        self.eventos = db["Economia_Eventos"]

    @staticmethod
    def _numero(valor, padrao=0.0):
        try:
            return max(0.0, float(valor if valor is not None else padrao))
        except (TypeError, ValueError):
            return float(padrao)

    @staticmethod
    def _nome(documento):
        return str(documento.get("territorio") or documento.get("reino") or documento.get("pais") or documento.get("cidade") or documento.get("nome") or "")

    def _registrar(self, territorio, tipo, titulo, descricao, impacto, prioridade="normal"):
        agora = datetime.now(timezone.utc)
        evento = {
            "guild_id": str(territorio.get("guild_id", "")),
            "tipo": "crises_financeiras" if tipo in {"crise_local", "escassez_regional", "desastre_natural"} else "anuncios_governamentais",
            "evento_economico": tipo,
            "titulo": titulo,
            "descricao": descricao,
            "territorio": self._nome(territorio),
            "impacto": impacto,
            "prioridade": prioridade,
            "criado_em": agora,
            "publicado": False,
        }
        self.acontecimentos.insert_one(evento)
        self.eventos.insert_one({
            "tipo": "evento_economico_mundial",
            "evento": tipo,
            "territorio": self._nome(territorio),
            "impacto": impacto,
            "criado_em": agora,
        })

    def _aplicar(self, territorio, tipo):
        nome = self._nome(territorio)
        impacto = random.randint(3, 12)
        prosperidade = self._numero(territorio.get("prosperidade"), 50)
        desenvolvimento = self._numero(territorio.get("desenvolvimento"), 50)
        estabilidade = self._numero(territorio.get("estabilidade"), 50)
        atualizacoes = {"ultimo_evento_economico": tipo, "ultimo_evento_em": datetime.now(timezone.utc)}

        if tipo == "descoberta_recurso":
            atualizacoes["prosperidade"] = min(100, prosperidade + impacto)
            atualizacoes["desenvolvimento"] = min(100, desenvolvimento + impacto * 0.5)
            titulo = "⛏️ Nova descoberta de recursos"
            descricao = f"Novos recursos foram encontrados em {nome}, aumentando o potencial econômico regional."
        elif tipo == "oportunidade_comercial":
            atualizacoes["prosperidade"] = min(100, prosperidade + impacto)
            titulo = "📈 Grande oportunidade comercial"
            descricao = f"Uma nova oportunidade comercial surgiu em {nome}."
        elif tipo == "crescimento_regional":
            atualizacoes["desenvolvimento"] = min(100, desenvolvimento + impacto)
            atualizacoes["prosperidade"] = min(100, prosperidade + impacto * 0.7)
            titulo = "🏙️ Crescimento econômico regional"
            descricao = f"A atividade econômica de {nome} está crescendo rapidamente."
        elif tipo == "escassez_regional":
            atualizacoes["prosperidade"] = max(0, prosperidade - impacto)
            titulo = "📦 Escassez regional"
            descricao = f"Uma escassez começou a afetar a economia de {nome}."
        elif tipo == "desastre_natural":
            atualizacoes["prosperidade"] = max(0, prosperidade - impacto)
            atualizacoes["estabilidade"] = max(0, estabilidade - impacto * 0.8)
            titulo = "🌪️ Desastre afeta a economia"
            descricao = f"Um desastre causou prejuízos econômicos em {nome}."
        elif tipo == "crise_local":
            atualizacoes["prosperidade"] = max(0, prosperidade - impacto)
            atualizacoes["desenvolvimento"] = max(0, desenvolvimento - impacto * 0.5)
            titulo = "📉 Crise econômica local"
            descricao = f"Uma crise econômica começou a afetar {nome}."
        else:
            atualizacoes["prosperidade"] = min(100, prosperidade + impacto * 0.6)
            titulo = "👥 Crescimento populacional"
            descricao = f"O crescimento populacional aumentou o potencial econômico de {nome}."

        self.territorios.update_one({"_id": territorio["_id"]}, {"$set": atualizacoes})
        prioridade = "alta" if tipo in {"crise_local", "desastre_natural"} else "normal"
        self._registrar(territorio, tipo, titulo, descricao, impacto, prioridade)
        return tipo

    def executar_ciclo(self):
        territorios = list(self.territorios.find({}))
        if not territorios:
            return {"evento_gerado": False, "motivo": "sem_territorios"}

        # Frequência controlada para evitar inundar os canais de acontecimentos.
        chance = 0.08
        if random.random() > chance:
            return {"evento_gerado": False, "motivo": "nenhum_evento_neste_ciclo"}

        territorio = random.choice(territorios)
        tipo = random.choice(self.TIPOS)
        resultado = self._aplicar(territorio, tipo)
        return {"evento_gerado": True, "tipo": resultado, "territorio": self._nome(territorio)}
