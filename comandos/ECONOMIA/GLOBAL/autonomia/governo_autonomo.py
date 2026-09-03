from datetime import datetime, timezone


class MotorGovernoAutonomo:
    """Governos NPC analisam sua situação e tomam decisões econômicas próprias."""

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.governos = db["Economia_Governos"]
        self.tesouros = db["Economia_Tesouros"]
        self.territorios = db["Economia_Territorios"]
        self.acontecimentos = db["Economia_Acontecimentos"]

    @staticmethod
    def _numero(valor, padrao=0.0):
        try:
            return max(0.0, float(valor if valor is not None else padrao))
        except (TypeError, ValueError):
            return float(padrao)

    def _territorio(self, governo):
        return governo.get("pais") or governo.get("pais_id") or governo.get("reino") or governo.get("reino_id")

    def _tesouro(self, governo):
        return self.tesouros.find_one({"guild_id": str(governo.get("guild_id")), "governo_id": str(governo.get("_id"))}) or {}

    def _registrar(self, governo, titulo, descricao, dados):
        self.acontecimentos.insert_one({
            "guild_id": str(governo.get("guild_id", "")),
            "tipo": "anuncios_governamentais",
            "titulo": titulo,
            "descricao": descricao,
            "dados": dados,
            "prioridade": "normal",
            "criado_em": datetime.now(timezone.utc),
            "publicado": False,
        })

    def _decidir(self, governo):
        territorio_nome = self._territorio(governo)
        territorio = self.territorios.find_one({"guild_id": str(governo.get("guild_id")), "$or": [{"nome": territorio_nome}, {"pais": territorio_nome}, {"reino": territorio_nome}]}) or {}
        tesouro = self._tesouro(governo)
        saldo = self._numero(tesouro.get("saldo_bronze"))
        prosperidade = self._numero(territorio.get("prosperidade"), 50)
        estabilidade = self._numero(territorio.get("estabilidade"), 50)
        desenvolvimento = self._numero(territorio.get("desenvolvimento"), 50)
        receita = self._numero(tesouro.get("receita_acumulada_bronze"))
        despesa = self._numero(tesouro.get("despesa_acumulada_bronze"))
        imposto = self._numero(governo.get("imposto_empresarial"), 0.10)
        gasto = self._numero(governo.get("gasto_publico_base_bronze"))

        # Prioridade: impedir colapso, depois recuperar economia e por fim investir.
        if estabilidade < 30:
            novo_gasto = max(gasto, saldo * 0.08)
            return "estabilizacao", {"gasto_publico_base_bronze": novo_gasto}, "🏛️ Governo prioriza a estabilidade", "Diante da baixa estabilidade regional, o governo aumentou suas medidas públicas."
        if prosperidade < 30 and saldo > 0:
            novo_gasto = max(gasto, saldo * 0.06)
            return "recuperacao", {"gasto_publico_base_bronze": novo_gasto}, "🏗️ Governo inicia recuperação econômica", "O tesouro foi direcionado para estimular a recuperação da economia regional."
        if receita > 0 and despesa > receita * 1.25:
            novo_imposto = min(0.35, imposto + 0.01)
            novo_gasto = max(0.0, gasto * 0.92)
            return "austeridade", {"imposto_empresarial": novo_imposto, "gasto_publico_base_bronze": novo_gasto}, "📉 Governo adota medidas fiscais", "O governo ajustou impostos e gastos para reduzir o desequilíbrio fiscal."
        if saldo < max(100.0, gasto * 2) and receita > despesa:
            novo_gasto = max(0.0, gasto * 0.90)
            return "reserva", {"gasto_publico_base_bronze": novo_gasto}, "💰 Governo reforça o tesouro", "Parte dos gastos foi reduzida para reconstruir a reserva pública."
        if desenvolvimento < 60 and saldo > 500:
            novo_gasto = max(gasto, saldo * 0.04)
            return "infraestrutura", {"gasto_publico_base_bronze": novo_gasto}, "🏗️ Governo investe em desenvolvimento", "O governo aumentou os investimentos públicos para desenvolver o território."
        if prosperidade > 70 and estabilidade > 65 and imposto > 0.03:
            return "reducao_imposto", {"imposto_empresarial": max(0.03, imposto - 0.005)}, "📈 Governo reduz impostos", "A situação econômica favorável permitiu uma pequena redução tributária."
        return "manutencao", {}, None, None

    def processar_governo(self, governo):
        # Governos explicitamente controlados por jogadores/administradores não são alterados sem autorização.
        if governo.get("autonomia") is False or governo.get("controlado_por_jogador"):
            return "ignorado"
        decisao, ajustes, titulo, descricao = self._decidir(governo)
        if ajustes:
            ajustes["ultima_decisao_autonoma"] = decisao
            ajustes["ultima_decisao_em"] = datetime.now(timezone.utc)
            self.governos.update_one({"_id": governo["_id"]}, {"$set": ajustes})
        if titulo:
            self._registrar(governo, titulo, descricao, {"decisao": decisao, "ajustes": ajustes, "territorio": self._territorio(governo)})
        return decisao

    def executar_ciclo(self):
        resultados = [self.processar_governo(g) for g in self.governos.find({})]
        return {
            "governos_analisados": len(resultados),
            "governos_ignorados": resultados.count("ignorado"),
            "decisoes": {acao: resultados.count(acao) for acao in set(resultados)},
        }
