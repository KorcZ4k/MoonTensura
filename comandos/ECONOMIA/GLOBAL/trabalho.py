from datetime import datetime, timezone


class MotorTrabalho:
    """Mercado de trabalho, salários, folha de pagamento e renda disponível."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.empregos = db["Economia_Empregos"]
        self.folhas = db["Economia_Folhas_Pagamento"]
        self.empresas = db["Economia_Empresas"]
        self.populacoes = db["Economia_Populacao"]

    def criar_emprego(self, empresa_id, governo_id, cargo, vagas, salario_bronze, produtividade=1.0):
        vagas = max(0, int(vagas))
        salario = max(0.0, float(salario_bronze))
        doc = {
            "empresa_id": str(empresa_id), "governo_id": str(governo_id),
            "cargo": str(cargo), "vagas": vagas, "ocupadas": 0,
            "salario_bronze": salario, "produtividade": max(0.01, float(produtividade)),
            "ativa": True, "criado_em": datetime.now(timezone.utc),
        }
        resultado = self.empregos.insert_one(doc)
        doc["_id"] = resultado.inserted_id
        return doc

    def contratar(self, emprego_id, quantidade=1):
        emprego = self.empregos.find_one({"_id": emprego_id, "ativa": True})
        if not emprego:
            return {"erro": "emprego_inexistente"}
        populacao = self.populacoes.find_one({"governo_id": emprego["governo_id"]})
        if not populacao:
            return {"erro": "populacao_inexistente"}
        disponiveis = max(0, int(populacao.get("desempregados", 0)))
        vagas = max(0, int(emprego.get("vagas", 0)) - int(emprego.get("ocupadas", 0)))
        contratados = min(max(0, int(quantidade)), disponiveis, vagas)
        if contratados <= 0:
            return {"erro": "sem_mao_de_obra_ou_vagas"}
        self.empregos.update_one({"_id": emprego_id}, {"$inc": {"ocupadas": contratados}})
        empregados = int(populacao.get("empregados", 0)) + contratados
        desempregados = max(0, int(populacao.get("desempregados", 0)) - contratados)
        total = max(1, int(populacao.get("quantidade", 1)))
        self.populacoes.update_one({"_id": populacao["_id"]}, {"$set": {"empregados": empregados, "desempregados": desempregados, "taxa_desemprego": desempregados / total, "atualizado_em": datetime.now(timezone.utc)}})
        return {"contratados": contratados, "empregados": empregados, "desempregados": desempregados}

    def folha_pagamento(self, governo_id=None):
        consulta = {"ativa": True}
        if governo_id is not None:
            consulta["governo_id"] = str(governo_id)
        total = 0.0; trabalhadores = 0; empresas_afetadas = set(); agora = datetime.now(timezone.utc)
        for emprego in self.empregos.find(consulta):
            ocupadas = int(emprego.get("ocupadas", 0))
            if ocupadas <= 0:
                continue
            valor = ocupadas * float(emprego.get("salario_bronze", 0))
            total += valor; trabalhadores += ocupadas; empresas_afetadas.add(emprego["empresa_id"])
            self.folhas.insert_one({"empresa_id": emprego["empresa_id"], "governo_id": emprego["governo_id"], "emprego_id": str(emprego["_id"]), "trabalhadores": ocupadas, "valor_bronze": valor, "data": agora})
            self.empresas.update_one({"_id": emprego["empresa_id"]}, {"$inc": {"caixa_bronze": -valor, "custos_bronze": valor, "folha_salarial_bronze": valor}})
        if governo_id is not None:
            pop = self.populacoes.find_one({"governo_id": str(governo_id)})
            if pop and total:
                self.populacoes.update_one({"_id": pop["_id"]}, {"$inc": {"renda_mensal_total_bronze": total}, "$set": {"ultima_folha": agora}})
        return {"folha_total_bronze": total, "trabalhadores": trabalhadores, "empresas": len(empresas_afetadas)}

    def ciclo_trabalho(self):
        resultados = []
        governos = self.empregos.distinct("governo_id", {"ativa": True})
        for governo_id in governos:
            resultados.append({"governo_id": governo_id, **self.folha_pagamento(governo_id)})
        return resultados
