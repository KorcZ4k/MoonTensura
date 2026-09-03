from datetime import datetime, timezone


class MotorMercadoTrabalho:
    """Mercado de trabalho com vagas, salários, contratação e desemprego."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.vagas = db["Economia_Vagas"]
        self.empregos = db["Economia_Empregos"]
        self.populacoes = db["Economia_Populacao"]
        self.historico = db["Economia_Mercado_Trabalho_Historico"]

    def criar_vaga(self, governo_id, empregador_id, cargo, salario_bronze, quantidade=1, qualificacao=0.0):
        doc = {"governo_id": str(governo_id), "empregador_id": str(empregador_id), "cargo": str(cargo), "salario_bronze": max(1.0, float(salario_bronze)), "quantidade": max(1, int(quantidade)), "preenchidas": 0, "qualificacao": max(0.0, min(1.0, float(qualificacao))), "ativa": True, "criada_em": datetime.now(timezone.utc)}
        self.vagas.insert_one(doc)
        return doc

    def contratar(self, vaga_id, trabalhador_id, qualificacao=0.0):
        vaga = self.vagas.find_one({"_id": vaga_id, "ativa": True})
        if not vaga: return {"erro": "vaga_nao_encontrada"}
        if vaga["preenchidas"] >= vaga["quantidade"]: return {"erro": "vaga_preenchida"}
        if float(qualificacao) < float(vaga.get("qualificacao", 0.0)): return {"erro": "qualificacao_insuficiente"}
        emprego = {"vaga_id": vaga_id, "governo_id": vaga["governo_id"], "empregador_id": vaga["empregador_id"], "trabalhador_id": str(trabalhador_id), "cargo": vaga["cargo"], "salario_bronze": vaga["salario_bronze"], "produtividade": max(0.1, min(2.0, 0.5 + float(qualificacao))), "ativo": True, "contratado_em": datetime.now(timezone.utc)}
        self.empregos.update_one({"trabalhador_id": emprego["trabalhador_id"], "ativo": True}, {"$set": {"ativo": False, "encerrado_em": datetime.now(timezone.utc)}})
        self.empregos.insert_one(emprego)
        self.vagas.update_one({"_id": vaga_id}, {"$inc": {"preenchidas": 1}, "$set": {"ativa": vaga["preenchidas"] + 1 < vaga["quantidade"]}})
        return emprego

    def processar_ciclo(self):
        resultados = []
        for populacao in self.populacoes.find():
            governo_id = str(populacao.get("governo_id", "global"))
            total = max(1, int(populacao.get("populacao", populacao.get("total", 1))))
            empregados = self.empregos.count_documents({"governo_id": governo_id, "ativo": True})
            vagas = self.vagas.aggregate([{ "$match": {"governo_id": governo_id, "ativa": True}}, {"$project": {"abertas": {"$subtract": ["$quantidade", "$preenchidas"]}}}, {"$group": {"_id": None, "total": {"$sum": "$abertas"}}}])
            vagas_doc = next(vagas, None)
            vagas_abertas = int(vagas_doc.get("total", 0)) if vagas_doc else 0
            desempregados = max(0, total - empregados)
            desemprego = desempregados / total
            salario_medio = 0.0
            salarios = list(self.empregos.find({"governo_id": governo_id, "ativo": True}, {"salario_bronze": 1}))
            if salarios: salario_medio = sum(float(x.get("salario_bronze", 0)) for x in salarios) / len(salarios)
            estado = {"governo_id": governo_id, "populacao_ativa": total, "empregados": empregados, "desempregados": desempregados, "vagas_abertas": vagas_abertas, "taxa_desemprego": desemprego, "salario_medio_bronze": salario_medio, "data": datetime.now(timezone.utc)}
            resultados.append(estado)
            self.historico.insert_one(estado)
        return {"mercados_processados": len(resultados), "resultados": resultados}
