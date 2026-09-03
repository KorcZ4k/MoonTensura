from datetime import datetime, timezone


class MotorCrisesDinamicas:
    """Etapa 8: detecta pressão econômica e inicia ou encerra crises automaticamente."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.empresas = db["Economia_Empresas"]
        self.populacoes = db["Economia_Populacoes"]
        self.mercados = db["Mercados"]
        self.creditos = db["Economia_Creditos"]
        self.crises = db["Economia_Crises"]
        self.acontecimentos = db["Economia_Acontecimentos"]

    @staticmethod
    def _numero(valor):
        try:
            return float(valor or 0)
        except (TypeError, ValueError):
            return 0.0

    def _registrar(self, guild_id, titulo, descricao, dados, prioridade="alta"):
        self.acontecimentos.insert_one({
            "guild_id": str(guild_id), "tipo": "crises_financeiras",
            "titulo": titulo, "descricao": descricao, "dados": dados,
            "prioridade": prioridade, "criado_em": datetime.now(timezone.utc),
            "publicado": False,
        })

    def _metricas(self, guild_id):
        populacoes = list(self.populacoes.find({"guild_id": str(guild_id)}))
        empresas = list(self.empresas.find({"guild_id": str(guild_id)}))
        mercados = list(self.mercados.find({"guild_id": str(guild_id)}))

        trabalhadores = sum(self._numero(p.get("trabalhadores")) for p in populacoes)
        desempregados = sum(self._numero(p.get("desempregados")) for p in populacoes)
        taxa_desemprego = desempregados / max(1, trabalhadores + desempregados)

        ativas = sum(1 for e in empresas if e.get("status", "ativa") == "ativa")
        falidas = sum(1 for e in empresas if e.get("status") == "falida")
        taxa_falencia = falidas / max(1, ativas + falidas)

        inadimplentes = self.creditos.count_documents({"guild_id": str(guild_id), "status": "inadimplente"})
        total_creditos = self.creditos.count_documents({"guild_id": str(guild_id)})
        taxa_inadimplencia = inadimplentes / max(1, total_creditos)

        escassez = 0
        for mercado in mercados:
            estoque = mercado.get("estoque") or {}
            for quantidade in estoque.values():
                if self._numero(quantidade) <= 0:
                    escassez += 1

        return {"taxa_desemprego": taxa_desemprego, "taxa_falencia": taxa_falencia, "taxa_inadimplencia": taxa_inadimplencia, "itens_em_escassez": escassez, "empresas": len(empresas), "mercados": len(mercados)}

    def _tipos_de_crise(self, metricas):
        crises = []
        if metricas["taxa_desemprego"] >= 0.20:
            crises.append(("desemprego", "⚠️ Crise de desemprego", "O desemprego atingiu um nível elevado e reduziu o consumo da população."))
        if metricas["taxa_falencia"] >= 0.15 and metricas["empresas"] >= 3:
            crises.append(("falencias", "📉 Crise empresarial", "Uma quantidade significativa de empresas encerrou suas atividades."))
        if metricas["taxa_inadimplencia"] >= 0.20:
            crises.append(("credito", "🏦 Crise de crédito", "A inadimplência empresarial atingiu níveis preocupantes."))
        if metricas["itens_em_escassez"] >= 3:
            crises.append(("escassez", "📦 Crise de abastecimento", "Diversos produtos ficaram sem estoque nos mercados."))
        return crises

    def executar_ciclo(self):
        guilds = set()
        for colecao in (self.empresas, self.populacoes, self.mercados):
            guilds.update(str(x.get("guild_id")) for x in colecao.find({}, {"guild_id": 1}) if x.get("guild_id"))

        iniciadas = 0
        encerradas = 0
        ativas = 0
        agora = datetime.now(timezone.utc)

        for guild_id in guilds:
            metricas = self._metricas(guild_id)
            tipos_detectados = {x[0]: x for x in self._tipos_de_crise(metricas)}
            crises_ativas = list(self.crises.find({"guild_id": guild_id, "status": "ativa"}))
            tipos_ativos = {c.get("tipo") for c in crises_ativas}

            for tipo, (codigo, titulo, descricao) in tipos_detectados.items():
                if tipo not in tipos_ativos:
                    self.crises.insert_one({"guild_id": guild_id, "tipo": codigo, "status": "ativa", "metricas_inicio": metricas, "iniciada_em": agora, "ultima_analise": agora})
                    self._registrar(guild_id, titulo, descricao, metricas)
                    iniciadas += 1

            for crise in crises_ativas:
                if crise.get("tipo") not in tipos_detectados:
                    self.crises.update_one({"_id": crise["_id"]}, {"$set": {"status": "encerrada", "encerrada_em": agora, "ultima_analise": agora}})
                    self._registrar(guild_id, "📈 Recuperação econômica", f"A crise de {crise.get('tipo')} apresentou melhora e foi encerrada.", metricas, "normal")
                    encerradas += 1
                else:
                    self.crises.update_one({"_id": crise["_id"]}, {"$set": {"ultima_analise": agora, "metricas_atuais": metricas}})
                    ativas += 1

        return {"guilds_analisadas": len(guilds), "crises_iniciadas": iniciadas, "crises_encerradas": encerradas, "crises_ativas": ativas}
