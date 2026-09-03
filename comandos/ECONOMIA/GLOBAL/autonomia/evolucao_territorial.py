from datetime import datetime, timezone


class MotorEvolucaoTerritorial:
    """Etapa 14: prosperidade, crescimento e decadência econômica territorial."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.territorios = db["Economia_Territorios"]
        self.empresas = db["Economia_Empresas"]
        self.populacoes = db["Economia_Populacoes"]
        self.mercados = db["Economia_Mercados"]
        self.acontecimentos = db["Economia_Acontecimentos"]

    @staticmethod
    def _numero(valor, padrao=0.0):
        try:
            return max(0.0, float(valor if valor is not None else padrao))
        except (TypeError, ValueError):
            return float(padrao)

    @staticmethod
    def _nome_territorio(documento):
        return str(documento.get("territorio") or documento.get("reino") or documento.get("pais") or documento.get("cidade") or "")

    def _registrar(self, guild_id, titulo, descricao, dados, prioridade="normal"):
        self.acontecimentos.insert_one({
            "guild_id": str(guild_id),
            "tipo": "anuncios_governamentais",
            "titulo": titulo,
            "descricao": descricao,
            "dados": dados,
            "prioridade": prioridade,
            "criado_em": datetime.now(timezone.utc),
            "publicado": False,
        })

    def _dados_territorio(self, nome):
        empresas = list(self.empresas.find({}))
        empresas_locais = [e for e in empresas if self._nome_territorio(e) == nome and e.get("status", "ativa") == "ativa"]
        populacoes = [p for p in self.populacoes.find({}) if self._nome_territorio(p) == nome]
        mercados = [m for m in self.mercados.find({}) if self._nome_territorio(m) == nome]

        populacao = sum(self._numero(p.get("populacao") or p.get("quantidade")) for p in populacoes)
        capacidade = sum(self._numero(e.get("capacidade_producao")) for e in empresas_locais)
        riqueza = sum(self._numero(e.get("capital") or e.get("saldo")) for e in empresas_locais)
        atividade = len(empresas_locais) * 8 + len(mercados) * 5 + min(30, capacidade / 100) + min(20, riqueza / 10000)
        return {"empresas": len(empresas_locais), "mercados": len(mercados), "populacao": populacao, "atividade": atividade}

    def processar_territorio(self, territorio):
        nome = self._nome_territorio(territorio)
        if not nome:
            return {"acao": "ignorado"}

        dados = self._dados_territorio(nome)
        desenvolvimento = self._numero(territorio.get("desenvolvimento"), 50.0)
        prosperidade = self._numero(territorio.get("prosperidade"), 50.0)
        estabilidade = self._numero(territorio.get("estabilidade"), 50.0)

        impulso = (dados["atividade"] - 25) / 25
        crescimento = max(-3.0, min(3.0, impulso + (estabilidade - 50) / 50))
        novo_desenvolvimento = max(0.0, min(100.0, desenvolvimento + crescimento))
        nova_prosperidade = max(0.0, min(100.0, prosperidade + crescimento * 0.8))

        nivel_anterior = str(territorio.get("nivel_economico", "estavel"))
        if novo_desenvolvimento >= 80:
            nivel = "metropole_próspera"
        elif novo_desenvolvimento >= 60:
            nivel = "desenvolvido"
        elif novo_desenvolvimento >= 40:
            nivel = "estavel"
        elif novo_desenvolvimento >= 20:
            nivel = "em_declinio"
        else:
            nivel = "critico"

        self.territorios.update_one({"_id": territorio["_id"]}, {"$set": {
            "desenvolvimento": novo_desenvolvimento,
            "prosperidade": nova_prosperidade,
            "nivel_economico": nivel,
            "atividade_empresarial": dados["atividade"],
            "populacao_economica": dados["populacao"],
            "atualizado_em": datetime.now(timezone.utc),
        }})

        if nivel != nivel_anterior:
            titulo = "📈 Território em crescimento" if novo_desenvolvimento > desenvolvimento else "📉 Território em decadência"
            self._registrar(territorio.get("guild_id"), titulo, f"{nome} mudou de nível econômico para {nivel}.", {"territorio": nome, "nivel_anterior": nivel_anterior, "novo_nivel": nivel, "desenvolvimento": novo_desenvolvimento}, "alta" if nivel in {"metropole_próspera", "critico"} else "normal")

        return {"acao": "processado", "crescimento": crescimento, "nivel": nivel, "prosperidade": nova_prosperidade}

    def executar_ciclo(self):
        resultados = [self.processar_territorio(t) for t in self.territorios.find({})]
        processados = [r for r in resultados if r.get("acao") == "processado"]
        return {
            "territorios_processados": len(processados),
            "territorios_em_crescimento": sum(1 for r in processados if r["crescimento"] > 0),
            "territorios_em_declinio": sum(1 for r in processados if r["crescimento"] < 0),
            "prosperidade_media": round(sum(r["prosperidade"] for r in processados) / len(processados), 2) if processados else 0,
        }
