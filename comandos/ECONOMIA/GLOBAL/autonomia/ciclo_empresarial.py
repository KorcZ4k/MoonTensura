from datetime import datetime, timezone


class MotorCicloEmpresarial:
    """Etapa 6: concorrência, expansão, recuperação e falência empresarial."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.empresas = db["Economia_Empresas"]
        self.acontecimentos = db["Economia_Acontecimentos"]

    @staticmethod
    def _numero(valor, padrao=0.0):
        try:
            return float(valor if valor is not None else padrao)
        except (TypeError, ValueError):
            return float(padrao)

    def _registrar(self, guild_id, titulo, descricao, dados, prioridade="normal"):
        self.acontecimentos.insert_one({
            "guild_id": str(guild_id),
            "tipo": "empresas",
            "titulo": titulo,
            "descricao": descricao,
            "dados": dados,
            "prioridade": prioridade,
            "criado_em": datetime.now(timezone.utc),
            "publicado": False,
        })

    def processar_empresa(self, empresa):
        agora = datetime.now(timezone.utc)
        caixa = self._numero(empresa.get("caixa_bronze"))
        receita = self._numero(empresa.get("receita_bronze"))
        custos = self._numero(empresa.get("custos_bronze"))
        lucro = receita - custos
        funcionarios = list(empresa.get("funcionarios") or [])
        capacidade = int(self._numero(empresa.get("capacidade_funcionarios"), max(1, len(funcionarios) + 5)))
        historico = list(empresa.get("historico_lucro") or [])[-5:]
        historico.append(lucro)
        lucro_medio = sum(historico) / len(historico)
        prejuizos = int(empresa.get("ciclos_prejuizo", 0))
        expansoes = int(empresa.get("expansoes", 0))
        status = empresa.get("status", "ativa")
        evento = None

        if status != "ativa":
            return {"empresa_id": empresa["_id"], "acao": "ignorada", "status": status}

        if lucro < 0:
            prejuizos += 1
        else:
            prejuizos = 0

        campos = {
            "historico_lucro": historico,
            "lucro_atual_bronze": lucro,
            "lucro_medio_bronze": lucro_medio,
            "ciclos_prejuizo": prejuizos,
            "atualizada_em": agora,
        }
        acao = "manter"

        # Crescimento gradual quando há lucro consistente e capital suficiente.
        if lucro_medio > 0 and caixa > max(1000.0, custos * 2) and len(funcionarios) < capacidade:
            campos["capacidade_funcionarios"] = capacidade + max(1, int(capacidade * 0.1))
            campos["expansoes"] = expansoes + 1
            campos["caixa_bronze"] = caixa - min(caixa * 0.05, max(100.0, lucro_medio * 0.2))
            acao = "expandir"
            evento = ("🏢 Empresa em expansão", "Uma empresa aumentou sua capacidade após manter resultados positivos.", "normal")

        # Recuperação reduz operações depois de prejuízos repetidos.
        elif prejuizos >= 3 and prejuizos < 6:
            nova_capacidade = max(1, int(capacidade * 0.85))
            campos["capacidade_funcionarios"] = nova_capacidade
            campos["em_recuperacao"] = True
            acao = "recuperacao"
            evento = ("⚠️ Empresa entrou em recuperação", "Uma empresa reduziu suas operações após acumular prejuízos consecutivos.", "alta")

        # Falência após crise prolongada e sem caixa para sustentar operações.
        elif prejuizos >= 6 and caixa <= max(0.0, custos * 0.25):
            campos["status"] = "falida"
            campos["falida_em"] = agora
            campos["em_recuperacao"] = False
            acao = "falir"
            evento = ("📉 Falência empresarial", "Uma empresa encerrou suas operações após não conseguir se recuperar de prejuízos prolongados.", "alta")

        elif empresa.get("em_recuperacao") and lucro > 0:
            campos["em_recuperacao"] = False
            acao = "recuperar"
            evento = ("📈 Empresa se recuperou", "Uma empresa voltou a apresentar resultados positivos e saiu do processo de recuperação.", "normal")

        self.empresas.update_one({"_id": empresa["_id"]}, {"$set": campos})

        if evento:
            self._registrar(
                empresa.get("guild_id"), evento[0], evento[1],
                {"empresa_id": str(empresa["_id"]), "acao": acao, "lucro": lucro, "caixa": caixa},
                evento[2],
            )

        return {"empresa_id": empresa["_id"], "acao": acao, "lucro": lucro, "prejuizos": prejuizos}

    def executar_ciclo(self):
        resultados = [self.processar_empresa(e) for e in self.empresas.find({"status": "ativa"})]
        return {
            "empresas_processadas": len(resultados),
            "expansoes": sum(1 for r in resultados if r.get("acao") == "expandir"),
            "recuperacoes": sum(1 for r in resultados if r.get("acao") in {"recuperacao", "recuperar"}),
            "falencias": sum(1 for r in resultados if r.get("acao") == "falir"),
            "resultados": resultados,
        }
