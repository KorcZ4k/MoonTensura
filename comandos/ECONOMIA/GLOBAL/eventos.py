import random
from datetime import datetime, timezone


class MotorEventosEconomicos:
    """Choques macro e microeconômicos persistentes e reversíveis pelo tempo."""

    TIPOS = {
        "escassez": {"descricao": "Redução da oferta e pressão altista sobre os preços."},
        "abundancia": {"descricao": "Aumento da oferta e pressão baixista sobre os preços."},
        "boom": {"descricao": "Expansão da renda, consumo e atividade econômica."},
        "recessao": {"descricao": "Contração da renda e da atividade econômica."},
        "guerra": {"descricao": "Aumento de custos logísticos e ruptura comercial."},
        "desastre": {"descricao": "Destruição de capacidade produtiva e choque de oferta."},
        "crise_financeira": {"descricao": "Contração de crédito e liquidez."},
        "inovacao": {"descricao": "Aumento de produtividade e redução de custos."},
    }

    def __init__(self, db, motor):
        self.db = db
        self.motor = motor
        self.eventos = db["Economia_Eventos"]

    def criar_evento(self, governo_id, tipo, intensidade, duracao=60, descricao=None):
        tipo = str(tipo).lower()
        if tipo not in self.TIPOS:
            return {"erro": "tipo_invalido"}
        intensidade = min(1.0, max(0.01, float(intensidade)))
        duracao = max(1, int(duracao))
        doc = {
            "governo_id": str(governo_id),
            "tipo": tipo,
            "intensidade": intensidade,
            "duracao_ciclos": duracao,
            "ciclos_restantes": duracao,
            "descricao": descricao or self.TIPOS[tipo]["descricao"],
            "ativo": True,
            "criado_em": datetime.now(timezone.utc),
        }
        self.eventos.insert_one(doc)
        return doc

    def eventos_ativos(self, governo_id=None):
        filtro = {"ativo": True}
        if governo_id is not None:
            filtro["governo_id"] = str(governo_id)
        return list(self.eventos.find(filtro))

    def processar_eventos(self):
        ativos = self.eventos_ativos()
        resultado = {"processados": 0, "impacto_inflacao": 0.0, "impactos": []}
        for evento in ativos:
            impacto = self._aplicar(evento)
            restante = int(evento.get("ciclos_restantes", 0)) - 1
            self.eventos.update_one({"_id": evento["_id"]}, {"$set": {
                "ciclos_restantes": max(0, restante),
                "ativo": restante > 0,
                "ultimo_processamento": datetime.now(timezone.utc),
            }})
            resultado["processados"] += 1
            resultado["impacto_inflacao"] += impacto.get("inflacao", 0.0)
            resultado["impactos"].append(impacto)
        return resultado

    def _aplicar(self, evento):
        tipo = evento["tipo"]
        intensidade = float(evento["intensidade"])
        governo_id = evento["governo_id"]
        inflacao = 0.0

        if tipo == "escassez":
            inflacao = intensidade * 0.006
            self.motor.mercados.update_many({}, {"$mul": {"oferta": max(0.01, 1 - intensidade * 0.20)}})

        elif tipo == "abundancia":
            inflacao = -intensidade * 0.004
            self.motor.mercados.update_many({}, {"$mul": {"oferta": 1 + intensidade * 0.20}})

        elif tipo == "boom":
            inflacao = intensidade * 0.002
            pop = self.db["Economia_Populacao"].find_one({"governo_id": governo_id})
            if pop:
                self.db["Economia_Populacao"].update_one({"_id": pop["_id"]}, {"$mul": {"renda_mensal_total_bronze": 1 + intensidade * 0.03}})

        elif tipo == "recessao":
            inflacao = -intensidade * 0.002
            pop = self.db["Economia_Populacao"].find_one({"governo_id": governo_id})
            if pop:
                taxa = min(1.0, float(pop.get("taxa_desemprego", 0)) + intensidade * 0.01)
                total = int(pop.get("quantidade", 0))
                desempregados = int(total * taxa)
                self.db["Economia_Populacao"].update_one({"_id": pop["_id"]}, {"$set": {
                    "taxa_desemprego": taxa,
                    "desempregados": desempregados,
                    "empregados": total - desempregados,
                }})

        elif tipo in {"guerra", "desastre"}:
            inflacao = intensidade * 0.008

        elif tipo == "crise_financeira":
            inflacao = -intensidade * 0.001
            self.motor.economia.update_one({"_id": "global"}, {"$mul": {"liquidez_ouro": max(0.01, 1 - intensidade * 0.02)}})

        elif tipo == "inovacao":
            inflacao = -intensidade * 0.003

        if inflacao:
            estado = self.motor.relatorio_global()
            indice = max(1.0, float(estado.get("indice_precos", 100.0)) * (1 + inflacao))
            self.motor.economia.update_one({"_id": "global"}, {"$set": {
                "indice_precos": indice,
                "ultimo_evento": tipo,
                "ultimo_evento_em": datetime.now(timezone.utc),
            }})

        return {"tipo": tipo, "governo_id": governo_id, "inflacao": inflacao}
