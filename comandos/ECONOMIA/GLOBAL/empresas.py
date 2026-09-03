from datetime import datetime, timezone


class MotorEmpresas:
    """Empresas, capital, patrimônio, lucro, dívida e falência."""

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.empresas = db["Economia_Empresas"]
        self.lancamentos = db["Economia_Lancamentos"]
        self.dividas = db["Economia_Dividas"]

    def criar_empresa(self, proprietario_id, nome, capital_inicial, tipo="comercio", guild_id=None):
        capital = max(0, float(capital_inicial))
        documento = {
            "proprietario_id": str(proprietario_id), "nome": str(nome),
            "tipo": str(tipo).lower(), "guild_id": str(guild_id) if guild_id else None,
            "caixa_bronze": capital, "patrimonio_bronze": capital,
            "receita_bronze": 0.0, "custos_bronze": 0.0,
            "impostos_bronze": 0.0, "lucro_liquido_bronze": 0.0,
            "divida_bronze": 0.0, "status": "ativa",
            "mercados": [], "funcionarios": [],
            "criada_em": datetime.now(timezone.utc),
            "atualizada_em": datetime.now(timezone.utc)
        }
        resultado = self.empresas.insert_one(documento)
        documento["_id"] = resultado.inserted_id
        return documento

    def registrar_lancamento(self, empresa_id, tipo, valor_bronze, descricao="", categoria="operacional"):
        empresa = self.empresas.find_one({"_id": empresa_id})
        if not empresa or empresa.get("status") != "ativa":
            return {"erro": "empresa_inativa"}
        valor = max(0.0, float(valor_bronze))
        tipo = tipo.lower()
        if tipo not in {"receita", "custo", "imposto", "aporte", "divida"}:
            return {"erro": "tipo_invalido"}

        inc = {"caixa_bronze": valor if tipo in {"receita", "aporte"} else -valor}
        if tipo == "receita": inc["receita_bronze"] = valor
        elif tipo == "custo": inc["custos_bronze"] = valor
        elif tipo == "imposto": inc["impostos_bronze"] = valor
        elif tipo == "divida":
            inc["divida_bronze"] = valor
            inc["caixa_bronze"] = valor

        self.empresas.update_one({"_id": empresa_id}, {"$inc": inc, "$set": {"atualizada_em": datetime.now(timezone.utc)}})
        self.lancamentos.insert_one({
            "empresa_id": empresa_id, "tipo": tipo, "categoria": categoria,
            "valor_bronze": valor, "descricao": descricao,
            "criado_em": datetime.now(timezone.utc)
        })
        return self.atualizar_balanco(empresa_id)

    def atualizar_balanco(self, empresa_id):
        empresa = self.empresas.find_one({"_id": empresa_id})
        if not empresa: return {"erro": "empresa_nao_encontrada"}
        receita = float(empresa.get("receita_bronze", 0))
        custos = float(empresa.get("custos_bronze", 0))
        impostos = float(empresa.get("impostos_bronze", 0))
        lucro = receita - custos - impostos
        caixa = float(empresa.get("caixa_bronze", 0))
        divida = float(empresa.get("divida_bronze", 0))
        patrimonio = caixa - divida
        status = "ativa"
        if caixa < 0 and patrimonio < 0:
            status = "falida"
        elif caixa < 0:
            status = "insolvente"
        self.empresas.update_one({"_id": empresa_id}, {"$set": {
            "lucro_liquido_bronze": lucro, "patrimonio_bronze": patrimonio,
            "status": status, "atualizada_em": datetime.now(timezone.utc)
        }})
        return self.empresas.find_one({"_id": empresa_id})

    def vincular_mercado(self, empresa_id, guild_id, channel_id):
        mercado = self.motor.mercado_do_canal(guild_id, channel_id)
        if not mercado: return {"erro": "mercado_nao_encontrado"}
        empresa = self.empresas.find_one({"_id": empresa_id})
        if not empresa: return {"erro": "empresa_nao_encontrada"}
        chave = f"{guild_id}:{channel_id}"
        self.empresas.update_one({"_id": empresa_id}, {"$addToSet": {"mercados": chave}})
        self.motor.mercados.update_one({"_id": mercado["_id"]}, {"$set": {"empresa_id": empresa_id}})
        return {"ok": True}

    def sincronizar_mercados(self):
        atualizadas = 0
        for empresa in self.empresas.find({"status": {"$in": ["ativa", "insolvente"]}}):
            receita = custos = 0.0
            for chave in empresa.get("mercados", []):
                try:
                    guild_id, channel_id = chave.split(":", 1)
                except ValueError:
                    continue
                mercado = self.motor.mercado_do_canal(guild_id, channel_id)
                if mercado:
                    receita += float(mercado.get("receita_bronze", 0))
                    custos += float(mercado.get("custos_operacionais_bronze", 0))
            self.empresas.update_one({"_id": empresa["_id"]}, {"$set": {"receita_bronze": receita, "custos_bronze": custos}})
            self.atualizar_balanco(empresa["_id"])
            atualizadas += 1
        return atualizadas
