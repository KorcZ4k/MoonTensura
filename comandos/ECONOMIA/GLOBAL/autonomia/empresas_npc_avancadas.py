from datetime import datetime, timezone


class MotorEmpresasNPCAvancadas:
    """Etapa 16: decisões autônomas para empresas sem proprietário jogador."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.empresas = db["Economia_Empresas"]
        self.mercados = db["Economia_Mercados"]
        self.eventos = db["Economia_Eventos"]
        self.acontecimentos = db["Economia_Acontecimentos"]

    @staticmethod
    def _numero(valor, padrao=0.0):
        try:
            return max(0.0, float(valor if valor is not None else padrao))
        except (TypeError, ValueError):
            return float(padrao)

    def _registrar(self, empresa, tipo, descricao, prioridade="normal"):
        self.acontecimentos.insert_one({
            "guild_id": str(empresa.get("guild_id", "")),
            "tipo": "empresas",
            "titulo": tipo,
            "descricao": descricao,
            "empresa_id": str(empresa["_id"]),
            "empresa": empresa.get("nome", "Empresa NPC"),
            "prioridade": prioridade,
            "criado_em": datetime.now(timezone.utc),
            "publicado": False,
        })

    def _eh_npc(self, empresa):
        dono = empresa.get("dono_id") or empresa.get("proprietario_id") or empresa.get("owner_id")
        return not dono or str(empresa.get("tipo_proprietario", "")).lower() == "npc"

    def _condicao_mercado(self, empresa):
        territorio = empresa.get("territorio") or empresa.get("cidade") or empresa.get("reino")
        concorrentes = 0
        for outra in self.empresas.find({"status": {"$ne": "falida"}}):
            if outra["_id"] == empresa["_id"]:
                continue
            outro_territorio = outra.get("territorio") or outra.get("cidade") or outra.get("reino")
            if territorio and territorio == outro_territorio:
                concorrentes += 1

        demanda = 50.0
        mercados = list(self.mercados.find({}))
        locais = [m for m in mercados if (m.get("territorio") or m.get("cidade") or m.get("reino")) == territorio]
        if locais:
            demanda = sum(self._numero(m.get("demanda"), 50) for m in locais) / len(locais)
        return demanda, concorrentes

    def processar_empresa(self, empresa):
        if not self._eh_npc(empresa):
            return "jogador"
        if empresa.get("status", "ativa") in {"falida", "encerrada"}:
            return "inativa"

        capital = self._numero(empresa.get("capital") or empresa.get("saldo"))
        receita = self._numero(empresa.get("receita_ciclo"))
        custos = self._numero(empresa.get("custos_ciclo"))
        demanda, concorrentes = self._condicao_mercado(empresa)
        margem = receita - custos
        estrategia = "manter"
        atualizacoes = {}

        if margem < 0 and capital < max(1000, custos * 2):
            atualizacoes["status"] = "falida"
            atualizacoes["estrategia_npc"] = "encerrar_operacoes"
            estrategia = "falir"
            self._registrar(empresa, "🏚️ Falência empresarial", f"{empresa.get('nome', 'Uma empresa NPC')} encerrou as operações por falta de capital.", "alta")
        elif margem < 0:
            capacidade = self._numero(empresa.get("capacidade_producao"), 100)
            atualizacoes["capacidade_producao"] = max(1.0, capacidade * 0.90)
            atualizacoes["estrategia_npc"] = "reduzir_operacoes"
            estrategia = "reduzir"
        elif demanda > 65 and margem > 0:
            capacidade = self._numero(empresa.get("capacidade_producao"), 100)
            atualizacoes["capacidade_producao"] = capacidade * 1.05
            atualizacoes["estrategia_npc"] = "expandir"
            estrategia = "expandir"
        elif concorrentes >= 5:
            preco = self._numero(empresa.get("preco_medio"), 100)
            atualizacoes["preco_medio"] = max(1.0, preco * 0.98)
            atualizacoes["estrategia_npc"] = "competir_por_preco"
            estrategia = "competir"
        else:
            atualizacoes["estrategia_npc"] = "manter_operacoes"

        trabalhadores = int(self._numero(empresa.get("trabalhadores"), 0))
        if estrategia == "expandir" and capital > 0:
            atualizacoes["trabalhadores"] = trabalhadores + max(1, trabalhadores // 10 or 1)
        elif estrategia == "reduzir" and trabalhadores > 0:
            atualizacoes["trabalhadores"] = max(0, trabalhadores - max(1, trabalhadores // 10))

        atualizacoes["ultima_decisao_npc"] = datetime.now(timezone.utc)
        self.empresas.update_one({"_id": empresa["_id"]}, {"$set": atualizacoes})
        return estrategia

    def executar_ciclo(self):
        contagem = {"expandir": 0, "reduzir": 0, "competir": 0, "falir": 0, "manter": 0, "jogador": 0, "inativa": 0}
        for empresa in self.empresas.find({}):
            resultado = self.processar_empresa(empresa)
            contagem[resultado] = contagem.get(resultado, 0) + 1

        return {
            "empresas_processadas": sum(v for k, v in contagem.items() if k not in {"jogador", "inativa"}),
            "empresas_expandidas": contagem["expandir"],
            "empresas_reduzidas": contagem["reduzir"],
            "empresas_em_competicao": contagem["competir"],
            "empresas_falidas": contagem["falir"],
            "empresas_de_jogadores_ignoradas": contagem["jogador"],
        }
