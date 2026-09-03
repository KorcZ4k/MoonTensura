from datetime import datetime, timezone


class IntegradorMercadoTrabalho:
    """Conecta empresas, empregos, salários, renda e produção."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.empresas = db["Economia_Empresas"]
        self.empregos = db["Economia_Empregos"]
        self.populacoes = db["Economia_Populacao"]
        self.historico = db["Economia_Trabalho_Integracao"]

    @staticmethod
    def _valor(doc, *chaves, padrao=0.0):
        for chave in chaves:
            if chave in doc:
                try:
                    return float(doc[chave] or 0)
                except (TypeError, ValueError):
                    pass
        return float(padrao)

    def _empregados_da_empresa(self, empresa_id):
        return self.empregos.count_documents({"empresa_id": empresa_id, "status": "ativo"})

    def _vagas_da_empresa(self, empresa_id):
        return self.empregos.count_documents({"empresa_id": empresa_id, "status": "vaga"})

    def processar_empresa(self, empresa, desemprego_global=0.05):
        empresa_id = empresa.get("_id")
        empregados = self._empregados_da_empresa(empresa_id)
        vagas = self._vagas_da_empresa(empresa_id)

        receita = self._valor(empresa, "receita_bronze", "receita")
        custos = self._valor(empresa, "custos_operacionais_bronze", "custos")
        lucro = receita - custos
        caixa = self._valor(empresa, "caixa_bronze", "caixa")
        demanda = self._valor(empresa, "demanda", "demanda_atual")
        oferta = self._valor(empresa, "oferta", "producao")

        capacidade = max(1, int(self._valor(empresa, "funcionarios_necessarios", "capacidade_trabalho", padrao=max(1, empregados))))
        ocupacao = empregados / capacidade
        produtividade = max(0.05, min(2.5, ocupacao))
        pressao_demanda = (demanda - oferta) / max(10.0, demanda + oferta + 10.0)

        # Escassez de trabalhadores reduz produção e aumenta pressão salarial.
        fator_producao = max(0.05, min(1.25, produtividade))
        nova_producao = max(0.0, oferta * fator_producao)

        # Empresas lucrativas e com excesso de demanda criam vagas.
        criar_vagas = 0
        if lucro > 0 and pressao_demanda > 0.05 and ocupacao >= 0.80:
            criar_vagas = max(1, int(capacidade * min(0.20, pressao_demanda)))

        # Empresas deficitárias reduzem vagas e podem demitir gradualmente.
        demissoes = 0
        if lucro < 0 and receita > 0 and empregados > 1:
            gravidade = min(0.25, abs(lucro) / max(1.0, receita))
            demissoes = max(0, int(empregados * gravidade))

        if criar_vagas:
            salario_base = self._valor(empresa, "salario_medio_bronze", "salario_base_bronze", padrao=1000)
            for _ in range(criar_vagas):
                self.empregos.insert_one({
                    "empresa_id": empresa_id,
                    "status": "vaga",
                    "salario_bronze": salario_base,
                    "criado_em": datetime.now(timezone.utc),
                })

        if demissoes:
            ativos = list(self.empregos.find({"empresa_id": empresa_id, "status": "ativo"}).limit(demissoes))
            for emprego in ativos:
                self.empregos.update_one({"_id": emprego["_id"]}, {"$set": {"status": "desempregado", "encerrado_em": datetime.now(timezone.utc), "motivo_saida": "resultado_empresarial"}})

        # Escassez de mão de obra pressiona salários para cima; desemprego elevado reduz a pressão.
        ajuste_salarial = (max(0.0, 1.0 - ocupacao) * 0.015) - (max(0.0, desemprego_global - 0.05) * 0.02)
        ajuste_salarial = max(-0.03, min(0.05, ajuste_salarial))

        self.empresas.update_one(
            {"_id": empresa_id},
            {"$set": {
                "empregados": empregados,
                "vagas_abertas": vagas + criar_vagas,
                "ocupacao_trabalho": ocupacao,
                "produtividade_trabalho": produtividade,
                "fator_producao_trabalho": fator_producao,
                "producao_ajustada_bronze": nova_producao,
                "ajuste_salarial": ajuste_salarial,
                "atualizado_em": datetime.now(timezone.utc),
            }},
        )

        if ajuste_salarial != 0:
            self.empregos.update_many(
                {"empresa_id": empresa_id, "status": {"$in": ["ativo", "vaga"]}},
                {"$mul": {"salario_bronze": 1.0 + ajuste_salarial}},
            )

        return {
            "empresa_id": empresa_id,
            "empregados": empregados,
            "novas_vagas": criar_vagas,
            "demissoes": demissoes,
            "produtividade": produtividade,
            "producao_ajustada": nova_producao,
        }

    def distribuir_salarios(self):
        total = 0.0
        quantidade = 0
        for emprego in self.empregos.find({"status": "ativo"}):
            salario = self._valor(emprego, "salario_bronze", "salario", padrao=0)
            if salario <= 0:
                continue
            total += salario
            quantidade += 1
            if emprego.get("governo_id"):
                self.populacoes.update_one(
                    {"governo_id": emprego["governo_id"]},
                    {"$inc": {"renda_trabalho_bronze": salario, "renda_disponivel_bronze": salario}},
                )
        return {"massa_salarial_bronze": total, "empregos_remunerados": quantidade}

    def processar_ciclo(self):
        total_ativos = self.empregos.count_documents({"status": "ativo"})
        total_desempregados = self.empregos.count_documents({"status": "desempregado"})
        for pop in self.populacoes.find():
            pea = self._valor(pop, "populacao_economicamente_ativa", "pea", "populacao")
            empregados = self.empregos.count_documents({"governo_id": pop.get("governo_id"), "status": "ativo"})
            desempregados = max(0.0, pea - empregados)
            self.populacoes.update_one(
                {"_id": pop["_id"]},
                {"$set": {"empregados": empregados, "desempregados": desempregados, "taxa_desemprego": desempregados / max(1.0, pea)}},
            )
            total_desempregados += desempregados

        pea_global = sum(self._valor(p, "populacao_economicamente_ativa", "pea", "populacao") for p in self.populacoes.find())
        desemprego_global = max(0.0, min(1.0, total_desempregados / max(1.0, pea_global)))

        resultados = [self.processar_empresa(empresa, desemprego_global) for empresa in self.empresas.find()]
        salarios = self.distribuir_salarios()

        resultado = {
            "data": datetime.now(timezone.utc),
            "empresas_processadas": len(resultados),
            "empregos_ativos": total_ativos,
            "taxa_desemprego": desemprego_global,
            **salarios,
            "resultados": resultados,
        }
        self.historico.insert_one(resultado)
        return resultado
