from database.python.mongodb import db
import json
import random
import datetime

# ==========================================
# COLLECTION
# ==========================================

jogadores = db["Jogadores"]


# ==========================================
# CARREGAR CONFIGURAÇÃO
# ==========================================

def _carregar_golpes():
    """Carrega os golpes do JSON"""
    try:
        with open('database/json/golpes.json', 'r', encoding='utf-8') as f:
            return json.load(f).get("golpes", {})
    except Exception as e:
        print(f"❌ Erro ao carregar golpes: {e}")
        return {}


def _carregar_monstros():
    """Carrega os monstros do JSON"""
    try:
        with open('database/json/monstros.json', 'r', encoding='utf-8') as f:
            return json.load(f).get("monstros", {})
    except Exception as e:
        print(f"❌ Erro ao carregar monstros: {e}")
        return {}


GOLPES = _carregar_golpes()
MONSTROS = _carregar_monstros()


# ==========================================
# OBTER JOGADOR
# ==========================================

def obter_jogador(user_id: str, guild_id: str):
    """Obtém os dados do jogador"""
    return jogadores.find_one({
        "ID": user_id,
        "guild_id": guild_id
    })


# ==========================================
# CALCULAR DANO
# ==========================================

def calcular_dano(atacante: dict, golpe_id: str, defensor: dict = None):
    """Calcula o dano baseado nos atributos do atacante e no golpe"""
    golpe = GOLPES.get(golpe_id)
    if not golpe:
        return 0
    
    # Pega os atributos usados no golpe
    atributos_usados = golpe.get("atributos", ["Força"])
    
    # Calcula a soma dos atributos
    soma_atributos = 0
    for atributo in atributos_usados:
        valor = atacante.get(atributo, 0)
        soma_atributos += valor
    
    # Calcula o dano base
    dano_base = golpe.get("dano_base", 10)
    multiplicador = golpe.get("multiplicador", 0.5)
    
    # Fórmula: (soma_atributos * multiplicador) + dano_base
    dano = int((soma_atributos * multiplicador) + dano_base)
    
    # Se tiver defensor, reduz o dano pela defesa
    if defensor:
        defesa = defensor.get("defesa", defensor.get("Defesa", 0))
        dano = max(1, dano - int(defesa * 0.3))
    
    return max(1, dano)


# ==========================================
# CRIAR MONSTRO INSTÂNCIA
# ==========================================

def criar_monstro(tipo: str, nivel: int = 1):
    """Cria uma instância de um monstro"""
    dados = MONSTROS.get(tipo)
    if not dados:
        return None
    
    # Escala o monstro baseado no nível
    escala = 1 + (nivel - 1) * 0.1
    
    monstro = {
        "id": tipo,
        "nome": dados["nome"],
        "emoji": dados["emoji"],
        "vida_maxima": int(dados["vida"] * escala),
        "vida": int(dados["vida"] * escala),
        "atributos": {},
        "dano_base": int(dados["dano_base"] * escala),
        "defesa": int(dados["defesa"] * escala),
        "velocidade": int(dados["velocidade"] * escala),
        "xp_recompensa": int(dados["xp_recompensa"] * escala),
        "hunos_recompensa": int(dados["hunos_recompensa"] * escala),
        "nivel": nivel,
        "tipo": "monstro"
    }
    
    # Copia os atributos
    for attr, valor in dados.get("atributos", {}).items():
        monstro["atributos"][attr] = int(valor * escala)
    
    return monstro


# ==========================================
# VERIFICAR SE PODE LUTAR
# ==========================================

def pode_lutar(user_id: str, guild_id: str):
    """Verifica se o jogador pode entrar em combate"""
    jogador = obter_jogador(user_id, guild_id)
    
    if not jogador:
        return {"pode": False, "mensagem": "Jogador não encontrado."}
    
    if jogador.get("Situação") == "morto":
        return {"pode": False, "mensagem": "Você está morto."}
    
    if jogador.get("Situação") == "ativo_combate":
        return {"pode": False, "mensagem": "Você já está em combate."}
    
    vida = jogador.get("Vida", 0)
    if vida <= 0:
        return {"pode": False, "mensagem": "Você está sem vida."}
    
    return {"pode": True}


# ==========================================
# INICIAR COMBATE
# ==========================================

def iniciar_combate(jogadores_ids: list, guild_id: str, monstros: list = None, pvp: bool = False):
    """Inicia um combate"""
    participantes = []
    
    # Adiciona os jogadores
    for user_id in jogadores_ids:
        jogador = obter_jogador(user_id, guild_id)
        if jogador:
            participantes.append({
                "id": user_id,
                "nome": jogador.get("Nome", f"Jogador_{user_id}"),
                "tipo": "jogador",
                "vida": jogador.get("Vida", 0),
                "vida_maxima": jogador.get("Vida_Maxima", 100),
                "mana": jogador.get("Mana", 0),
                "mana_maxima": jogador.get("Mana Total", 100),
                "velocidade": jogador.get("Velocidade", 50),
                "defesa": jogador.get("Defesa", 0),
                "atributos": {
                    "Força": jogador.get("Força", 0),
                    "Defesa": jogador.get("Defesa", 0),
                    "Velocidade": jogador.get("Velocidade", 0),
                    "Destreza": jogador.get("Destreza", 0),
                    "Vitalidade": jogador.get("Vitalidade", 0),
                    "Magia": jogador.get("Magia", 0),
                    "Inteligencia": jogador.get("inteligencia", 0),
                    "Sorte": jogador.get("Sorte", 0)
                }
            })
    
    # Adiciona os monstros
    if monstros:
        for monstro_data in monstros:
            monstro = criar_monstro(monstro_data["tipo"], monstro_data.get("nivel", 1))
            if monstro:
                participantes.append(monstro)
    
    # Ordena por velocidade (decrescente)
    participantes.sort(key=lambda x: x.get("velocidade", 0), reverse=True)
    
    return {
        "participantes": participantes,
        "turno_atual": 0,
        "rodada": 0,
        "pvp": pvp,
        "ativo": True,
        "historico": [],
        "fugiu": False
    }


# ==========================================
# EXECUTAR AÇÃO
# ==========================================

def executar_acao(combate: dict, usuario_id: str, acao: str, alvo_id: str = None):
    """Executa uma ação no combate"""
    if not combate["ativo"]:
        return {"sucesso": False, "mensagem": "Combate já terminou."}
    
    # Encontra o participante atual
    participante_atual = combate["participantes"][combate["turno_atual"]]
    
    if participante_atual["id"] != usuario_id:
        return {"sucesso": False, "mensagem": "Não é sua vez."}
    
    # Verifica se é um jogador
    if participante_atual["tipo"] != "jogador":
        return {"sucesso": False, "mensagem": "Não é um jogador."}
    
    # Busca o golpe
    golpe = GOLPES.get(acao)
    if not golpe:
        return {"sucesso": False, "mensagem": f"Ação {acao} não encontrada."}
    
    # Verifica mana
    custo_mana = golpe.get("custo_mana", 0)
    if participante_atual["mana"] < custo_mana:
        return {"sucesso": False, "mensagem": f"Mana insuficiente. Precisa de {custo_mana}."}
    
    # Processa defesa/esquiva
    if golpe.get("tipo") == "defesa":
        return _processar_defesa(combate, usuario_id, acao)
    
    # Encontra o alvo
    alvo = None
    if alvo_id:
        for p in combate["participantes"]:
            if p["id"] == alvo_id:
                alvo = p
                break
    else:
        # Se não especificou alvo e só tem 2 participantes, ataca o outro
        if len(combate["participantes"]) == 2:
            for p in combate["participantes"]:
                if p["id"] != usuario_id:
                    alvo = p
                    break
    
    if not alvo:
        return {"sucesso": False, "mensagem": "Alvo não encontrado."}
    
    # Calcula dano
    dano = calcular_dano(participante_atual, acao, alvo)
    
    # Aplica dano
    alvo["vida"] = max(0, alvo["vida"] - dano)
    
    # Consome mana
    participante_atual["mana"] = max(0, participante_atual["mana"] - custo_mana)
    
    # Atualiza no MongoDB
    _atualizar_participante(participante_atual)
    _atualizar_participante(alvo)
    
    # Registra no histórico
    mensagem = f"{participante_atual['nome']} usou **{golpe['nome']}** em {alvo['nome']} causando **{dano}** de dano!"
    combate["historico"].append(mensagem)
    
    # Verifica se o alvo morreu
    if alvo["vida"] <= 0:
        mensagem_morte = f"💀 **{alvo['nome']} foi derrotado!**"
        combate["historico"].append(mensagem_morte)
        
        # Remove o alvo da lista de participantes
        combate["participantes"] = [p for p in combate["participantes"] if p["id"] != alvo["id"]]
        
        # Verifica se o combate terminou
        if _verificar_fim_combate(combate):
            return {"sucesso": True, "mensagem": mensagem, "combate_terminou": True, "historico": combate["historico"]}
    
    # Avança o turno
    combate["turno_atual"] = (combate["turno_atual"] + 1) % len(combate["participantes"])
    
    # Se o turno atual for 0, nova rodada
    if combate["turno_atual"] == 0:
        combate["rodada"] += 1
    
    return {
        "sucesso": True,
        "mensagem": mensagem,
        "combate_terminou": False,
        "historico": combate["historico"],
        "turno_atual": combate["turno_atual"],
        "rodada": combate["rodada"],
        "participantes": combate["participantes"]
    }


def _processar_defesa(combate: dict, usuario_id: str, acao: str):
    """Processa ação de defesa/esquiva"""
    participante = None
    for p in combate["participantes"]:
        if p["id"] == usuario_id:
            participante = p
            break
    
    if not participante:
        return {"sucesso": False, "mensagem": "Participante não encontrado."}
    
    golpe = GOLPES.get(acao)
    custo_mana = golpe.get("custo_mana", 0)
    
    if participante["mana"] < custo_mana:
        return {"sucesso": False, "mensagem": f"Mana insuficiente. Precisa de {custo_mana}."}
    
    participante["mana"] = max(0, participante["mana"] - custo_mana)
    participante["defesa_ativa"] = acao
    
    _atualizar_participante(participante)
    
    mensagem = f"{participante['nome']} usou **{golpe['nome']}**!"
    combate["historico"].append(mensagem)
    
    # Avança o turno
    combate["turno_atual"] = (combate["turno_atual"] + 1) % len(combate["participantes"])
    
    if combate["turno_atual"] == 0:
        combate["rodada"] += 1
    
    return {
        "sucesso": True,
        "mensagem": mensagem,
        "combate_terminou": False,
        "historico": combate["historico"]
    }


def _atualizar_participante(participante: dict):
    """Atualiza os dados do participante no MongoDB"""
    if participante["tipo"] == "jogador":
        jogadores.update_one(
            {
                "ID": participante["id"],
                "guild_id": None  # Será passado na função chamadora
            },
            {
                "$set": {
                    "Vida": participante["vida"],
                    "Mana": participante["mana"]
                }
            }
        )


def _verificar_fim_combate(combate: dict):
    """Verifica se o combate terminou"""
    jogadores_vivos = [p for p in combate["participantes"] if p["tipo"] == "jogador" and p["vida"] > 0]
    monstros_vivos = [p for p in combate["participantes"] if p["tipo"] == "monstro" and p["vida"] > 0]
    
    if combate["pvp"]:
        # PvP: só termina quando só sobrar 1 jogador vivo
        return len(jogadores_vivos) <= 1
    else:
        # PvE: termina quando não tem monstros ou não tem jogadores
        return len(monstros_vivos) == 0 or len(jogadores_vivos) == 0


def fugir(combate: dict, usuario_id: str):
    """Tenta fugir do combate (15% de chance)"""
    participante = None
    for p in combate["participantes"]:
        if p["id"] == usuario_id:
            participante = p
            break
    
    if not participante:
        return {"sucesso": False, "mensagem": "Participante não encontrado."}
    
    # 15% de chance de fugir
    if random.random() < 0.15:
        # Perde 50% da mana
        participante["mana"] = int(participante["mana"] * 0.5)
        _atualizar_participante(participante)
        
        combate["fugiu"] = True
        combate["ativo"] = False
        
        # Remove o jogador do combate
        combate["participantes"] = [p for p in combate["participantes"] if p["id"] != usuario_id]
        
        mensagem = f"🏃 **{participante['nome']} conseguiu fugir!** (Perdeu 50% da mana)"
        combate["historico"].append(mensagem)
        
        return {
            "sucesso": True,
            "fugiu": True,
            "mensagem": mensagem,
            "historico": combate["historico"]
        }
    else:
        mensagem = f"❌ **{participante['nome']} tentou fugir, mas falhou!**"
        combate["historico"].append(mensagem)
        
        # Avança o turno
        combate["turno_atual"] = (combate["turno_atual"] + 1) % len(combate["participantes"])
        
        return {
            "sucesso": False,
            "fugiu": False,
            "mensagem": mensagem,
            "historico": combate["historico"]
        }