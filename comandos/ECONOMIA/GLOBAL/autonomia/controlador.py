from datetime import datetime, timezone


class ControladorAutonomiaEmpresas:
    """Etapa 1: identifica empresas sem dono e define seu modo de gestão."""

    MODOS = {"jogador", "automatico", "estatal", "misto"}

    def __init__(self, db, motor=None):
        self.db = db
        self.motor = motor
        self.empresas = db["Economia_Empresas"]
        self.eventos = db["Economia_Eventos"]

    @staticmethod
    def empresa_sem_dono(empresa):
        dono = empresa.get("proprietario_id")
        return dono is None or str(dono).strip().lower() in {"", "none", "null", "npc", "automatico"}

    def preparar_empresa(self, empresa):
        automatico = self.empresa_sem_dono(empresa)
        modo_atual = str(empresa.get("gestao", "")).lower()
        modo = modo_atual if modo_atual in self.MODOS else ("automatico" if automatico else "jogador")
        estado = {
            "gestao": modo,
            "autonomia": {
                "ativa": modo in {"automatico", "estatal", "misto"},
                "decisoes_por_ciclo": 0,
                "ultima_decisao": None,
                "ultimo_ciclo": None,
                "nivel": 1,
            },
            "atualizada_em": datetime.now(timezone.utc),
        }
        self.empresas.update_one({"_id": empresa["_id"]}, {"$set": estado})
        return self.empresas.find_one({"_id": empresa["_id"]})

    def preparar_empresas_existentes(self):
        preparadas = 0
        automaticas = 0
        for empresa in self.empresas.find({}):
            empresa_atualizada = self.preparar_empresa(empresa)
            preparadas += 1
            if empresa_atualizada.get("autonomia", {}).get("ativa"):
                automaticas += 1
        return {"empresas": preparadas, "automaticas": automaticas}

    def definir_gestao(self, empresa_id, modo):
        modo = str(modo).lower().strip()
        if modo not in self.MODOS:
            return {"erro": "modo_invalido", "modos": sorted(self.MODOS)}
        empresa = self.empresas.find_one({"_id": empresa_id})
        if not empresa:
            return {"erro": "empresa_nao_encontrada"}
        ativa = modo in {"automatico", "estatal", "misto"}
        self.empresas.update_one({"_id": empresa_id}, {"$set": {
            "gestao": modo,
            "autonomia.ativa": ativa,
            "atualizada_em": datetime.now(timezone.utc),
        }})
        return self.empresas.find_one({"_id": empresa_id})

    def executar_ciclo_base(self):
        total = 0
        automaticas = 0
        for empresa in self.empresas.find({"status": {"$in": ["ativa", "insolvente"]}}):
            if "gestao" not in empresa or "autonomia" not in empresa:
                empresa = self.preparar_empresa(empresa)
            if not empresa.get("autonomia", {}).get("ativa", False):
                continue
            automaticas += 1
            self.empresas.update_one({"_id": empresa["_id"]}, {"$set": {
                "autonomia.ultimo_ciclo": datetime.now(timezone.utc),
                "autonomia.ultima_decisao": "aguardando_modulos_de_decisao",
                "atualizada_em": datetime.now(timezone.utc),
            }})
            total += 1
        return {"processadas": total, "automaticas": automaticas}
