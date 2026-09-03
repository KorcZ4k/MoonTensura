from datetime import datetime, timezone


class MotorEmpresasNPCAvancadas:
    """Decisões autônomas usando o esquema financeiro oficial das empresas."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.empresas = db["Economia_Empresas"]
        # Coleção oficial; mantém fallback para instalações antigas.
        self.mercados = db["Mercados"]
        self.mercados_legados = db["Economia_Mercados"]
        self.acontecimentos = db["Economia_Acontecimentos"]

    @staticmethod
    def _numero(valor, padrao=0.0):
        try:
            return max(0.0, float(valor if valor is not None else padrao))
        except (TypeError, ValueError):
            return float(padrao)

    @classmethod
    def _campo(cls, documento, *campos, padrao=0.0):
        for campo in campos:
            if documento.get(campo) is not None:
                return cls._numero(documento.get(campo), padrao)
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
        gestao = str(empresa.get("gestao", "")).lower()
        if gestao in {"automatico", "estatal"}:
            return True
        if empresa.get("autonomia", {}).get("ativa"):
            return True
        dono = empresa.get("dono_id") or empresa.get("proprietario_id") or empresa.get("owner_id")
        return not dono or str(empresa.get("tipo_proprietario", "")).lower() == "npc"

    def _mercados_locais(self, territorio):
        locais = list(self.mercados.find({}))
        if not locais:
            locais = list(self.mercados_legados.find({}))
        return [m for m in locais if (m.get("territorio") or m.get("cidade") or m.get("reino")) == territorio]

    def _condicao_mercado(self, empresa):
        territorio = empresa.get("territorio") or empresa.get("cidade") or empresa.get("reino")
        concorrentes = 0
        for outra in self.empresas.find({"status": {"$ne": "falida"}}):
            if outra["_id"] != empresa["_id"] and territorio and (outra.get("territorio") or outra.get("cidade") or outra.get("reino")) == territorio:
                concorrentes += 1
        locais = self._mercados_locais(territorio)
        demanda = 50.0 if not locais else sum(self._campo(m, "demanda", padrao=50) for m in locais) / len(locais)
        return demanda, concorrentes

    def processar_empresa(self, empresa):
        if not self._eh_npc(empresa):
            return "jogador"
        if empresa.get("status", "ativa") in {"falida", "encerrada"}:
            return "inativa"

        capital = self._campo(empresa, "caixa_bronze", "capital_bronze", "capital", "saldo_bronze", "saldo")
        receita = self._campo(empresa, "receita_bronze", "receita_ciclo", "receita")
        custos = self._campo(empresa, "custos_bronze", "custos_ciclo", "custos")
        demanda, concorrentes = self._condicao_mercado(empresa)
        margem = receita - custos
        estrategia = "manter"
        atualizacoes = {}

        if margem < 0 and capital < max(1000, custos * 2):
            atualizacoes.update({"status": "falida", "estrategia_npc": "encerrar_operacoes"})
            estrategia = "falir"
            self._registrar(empresa, "🏚️ Falência empresarial", f"{empresa.get('nome', 'Uma empresa NPC')} encerrou as operações por falta de capital.", "alta")
        elif margem < 0:
            capacidade = self._campo(empresa, "capacidade_producao", "capacidade", padrao=100)
            atualizacoes.update({"capacidade_producao": max(1.0, capacidade * 0.90), "estrategia_npc": "reduzir_operacoes"})
            estrategia = "reduzir"
        elif demanda > 65 and margem > 0:
            capacidade = self._campo(empresa, "capacidade_producao", "capacidade", padrao=100)
            atualizacoes.update({"capacidade_producao": capacidade * 1.05, "estrategia_npc": "expandir"})
            estrategia = "expandir"
        elif concorrentes >= 5:
            preco = self._campo(empresa, "preco_medio", "preco_base", padrao=100)
            atualizacoes.update({"preco_medio": max(1.0, preco * 0.98), "estrategia_npc": "competir_por_preco"})
            estrategia = "competir"
        else:
            atualizacoes["estrategia_npc"] = "manter_operacoes"

        trabalhadores = int(self._campo(empresa, "trabalhadores", "funcionarios", padrao=0))
        if estrategia == "expandir" and capital > 0:
            atualizacoes["trabalhadores"] = trabalhadores + max(1, trabalhadores // 10 or 1)
        elif estrategia == "reduzir" and trabalhadores > 0:
            atualizacoes["trabalhadores"] = max(0, trabalhadores - max(1, trabalhadores // 10))

        atualizacoes.update({
            "ultima_decisao_npc": datetime.now(timezone.utc),
            "autonomia.ultima_decisao": estrategia,
            "autonomia.ultimo_ciclo": datetime.now(timezone.utc),
        })
        self.empresas.update_one({"_id": empresa["_id"]}, {"$set": atualizacoes})
        return estrategia

    def executar_ciclo(self):
        contagem = {"expandir": 0, "reduzir": 0, "competir": 0, "falir": 0, "manter": 0, "jogador": 0, "inativa": 0}
        for empresa in self.empresas.find({}):
            resultado = self.processar_empresa(empresa)
            contagem[resultado] = contagem.get(resultado, 0) + 1
        return {"empresas_processadas": sum(v for k, v in contagem.items() if k not in {"jogador", "inativa"}), "empresas_expandidas": contagem["expandir"], "empresas_reduzidas": contagem["reduzir"], "empresas_em_competicao": contagem["competir"], "empresas_falidas": contagem["falir"], "empresas_de_jogadores_ignoradas": contagem["jogador"]}
