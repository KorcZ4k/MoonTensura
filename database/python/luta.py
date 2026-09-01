from database.python.mongodb import db
import json
import random

# ==========================================
# CARREGAR CONFIGURAÇÃO
# ==========================================

def _carregar_golpes():
    try:
        with open('database/json/golpes.json', 'r', encoding='utf-8') as f:
            return json.load(f).get("golpes", {})
    except:
        return {}

def _carregar_monstros():
    try:
        with open('database/json/monstros.json', 'r', encoding='utf-8') as f:
            return json.load(f).get("monstros", {})
    except:
        return {}

GOLPES = _carregar_golpes()
MONSTROS = _carregar_monstros()


# ==========================================
# OBTER JOGADOR
# ==========================================

def obter_jogador(user_id: str, guild_id: str):
    return db["Jogadores"].find_one({
        "ID": user_id,
        "guild_id": guild_id
    })


# ==========================================
# CRIAR PARTICIPANTE JOGADOR
# ==========================================

def criar_participante_jogador(user_id: str, guild_id: str):
    jogador = obter_jogador(user_id, guild_id)
    if not jogador:
        return None
    
    forca = jogador.get("Força", 10)
    defesa = jogador.get("Defesa", 10)
    defesa_total = (forca + defesa) * 2
    
    return {
        "id": user_id,
        "nome": jogador.get("Nome", f"Jogador_{user_id}"),
        "tipo": "jogador",
        "vida": jogador.get("Vida", 100),
        "vida_maxima": jogador.get("Vida_Maxima", 100),
        "mana": jogador.get("Mana", 50),
        "velocidade": jogador.get("Velocidade", 50),
        "defesa": defesa_total,
        "Força": forca,
        "Destreza": jogador.get("Destreza", 10),
        "defesa_ativa": False,
        "esquiva_ativa": False
    }


# ==========================================
# CRIAR MONSTRO
# ==========================================

def criar_monstro(tipo: str, nivel: int = 1):
    """Cria um monstro com atributos baseados no nível"""
    dados = MONSTROS.get(tipo)
    if not dados:
        return None
    
    # Verifica se o nível está dentro do permitido
    nivel_minimo = dados.get("nivel_minimo", 1)
    nivel_maximo = dados.get("nivel_maximo", 99)
    
    if nivel < nivel_minimo:
        nivel = nivel_minimo
    if nivel > nivel_maximo:
        nivel = nivel_maximo
    
    # Fator de escala baseado no nível (cada nível aumenta 0.75)
    fator_escala = 1 + (nivel - 1) * 0.75
    
    # Pega os atributos base
    atributos_base = dados.get("atributos_base", {})
    
    # Aplica o fator de escala aos atributos
    forca = int(atributos_base.get("Força", 10) * fator_escala)
    defesa = int(atributos_base.get("Defesa", 10) * fator_escala)
    velocidade = int(atributos_base.get("Velocidade", 20) * fator_escala)
    destreza = int(atributos_base.get("Destreza", 10) * fator_escala)
    
    # Defesa total = (Força + Defesa) * 2
    defesa_total = (forca + defesa) * 2
    
    # Vida base com escala
    vida_base = dados.get("vida_base", 50)
    vida = int(vida_base * fator_escala)
    
    # Dano base com escala
    dano_base = int(dados.get("dano_base", 10) * fator_escala)
    
    # Recompensas com escala
    xp_recompensa = int(dados.get("xp_recompensa", 20) * fator_escala)
    hunos_recompensa = int(dados.get("hunos_recompensa", 10) * fator_escala)
    
    return {
        "id": tipo,
        "nome": dados["nome"],
        "emoji": dados["emoji"],
        "vida": vida,
        "vida_maxima": vida,
        "Força": forca,
        "Defesa": defesa_total,
        "Velocidade": velocidade,
        "Destreza": destreza,
        "dano_base": dano_base,
        "xp_recompensa": xp_recompensa,
        "hunos_recompensa": hunos_recompensa,
        "nivel": nivel,
        "nivel_minimo": nivel_minimo,
        "nivel_maximo": nivel_maximo,
        "tipo": "monstro",
        "defesa_ativa": True,
        "esquiva_ativa": True
    }

# ==========================================
# CALCULAR DANO
# ==========================================

def calcular_dano(atacante, defensor=None):
    # Esquiva do defensor
    if defensor and defensor.get("esquiva_ativa", False):
        if random.random() < 0.40:
            defensor["esquiva_ativa"] = False
            return 0, "esquivou"
        defensor["esquiva_ativa"] = False
    
    # Defesa do defensor
    reducao = 0
    if defensor and defensor.get("defesa_ativa", False):
        reducao = 0.5
        defensor["defesa_ativa"] = False
    
    # Dano base
    if atacante["tipo"] == "jogador":
        dano = int((atacante.get("Força", 10) + atacante.get("Destreza", 10)) / 2) + random.randint(1, 10)
    else:
        dano = atacante.get("dano_base", 10) + random.randint(1, 15)
    
    # Aplica defesa
    if defensor:
        defesa = defensor.get("defesa", 0)
        dano = max(1, dano - int(defesa * 0.1))
        if reducao > 0:
            dano = int(dano * (1 - reducao))
    
    return max(1, dano), "normal"


# ==========================================
# VERIFICAR SE PODE LUTAR
# ==========================================

def pode_lutar(user_id: str, guild_id: str):
    jogador = obter_jogador(user_id, guild_id)
    if not jogador:
        return {"pode": False, "mensagem": "Jogador não encontrado."}
    if jogador.get("Situação") == "morto":
        return {"pode": False, "mensagem": "❌ Você está morto."}
    if jogador.get("Situação") == "ativo_combate":
        return {"pode": False, "mensagem": "❌ Você já está em combate."}
    if jogador.get("Vida", 0) <= 0:
        return {"pode": False, "mensagem": "❌ Você está sem vida."}
    return {"pode": True}


# ==========================================
# FINALIZAR COMBATE
# ==========================================

def finalizar_combate(combate):
    guild_id = combate["guild_id"]
    
    # Atualiza jogadores
    for p in combate["participantes"]:
        if p["tipo"] == "jogador":
            db["Jogadores"].update_one(
                {"ID": p["id"], "guild_id": guild_id},
                {"$set": {"Situação": "ativo", "Vida": p["vida"], "Mana": p["mana"]}}
            )
    
    # Recompensas
    recompensas = None
    if not combate.get("pvp", False):
        jogadores_vivos = [p for p in combate["participantes"] if p["tipo"] == "jogador" and p["vida"] > 0]
        monstros_mortos = [p for p in combate["participantes"] if p["tipo"] == "monstro" and p["vida"] <= 0]
        
        if jogadores_vivos and monstros_mortos:
            xp_total = sum(p.get("xp_recompensa", 0) for p in monstros_mortos)
            hunos_total = sum(p.get("hunos_recompensa", 0) for p in monstros_mortos)
            
            if xp_total > 0 or hunos_total > 0:
                for p in jogadores_vivos:
                    db["Jogadores"].update_one(
                        {"ID": p["id"], "guild_id": guild_id},
                        {"$inc": {"XP": xp_total, "Hunos": hunos_total}}
                    )
                recompensas = {"xp": xp_total, "hunos": hunos_total}
    
    # Se todos morreram
    jogadores_vivos = [p for p in combate["participantes"] if p["tipo"] == "jogador" and p["vida"] > 0]
    if not jogadores_vivos:
        for p in combate["participantes"]:
            if p["tipo"] == "jogador":
                db["Jogadores"].update_one(
                    {"ID": p["id"], "guild_id": guild_id},
                    {"$set": {"Situação": "morto", "Vida": 0}}
                )
    
    return recompensas