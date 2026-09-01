from database.python.mongodb import db
import datetime
import json
import random

# ==========================================
# COLLECTION
# ==========================================

jogadores = db["Jogadores"]


# ==========================================
# CARREGAR CONFIGURAÇÃO
# ==========================================

def _carregar_config_treino():
    """Carrega a configuração dos treinos do JSON"""
    try:
        with open('database/json/treino.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erro ao carregar configuração de treino: {e}")
        return {
            "treinos": {
                "leve": {
                    "nome": "Treino Leve",
                    "emoji": "🏃",
                    "nivel_minimo": 1,
                    "cooldown_horas": 12,
                    "min_aumento": 0.1,
                    "max_aumento": 0.25
                },
                "medio": {
                    "nome": "Treino Médio",
                    "emoji": "💪",
                    "nivel_minimo": 10,
                    "cooldown_horas": 15,
                    "min_aumento": 0.2,
                    "max_aumento": 0.4
                },
                "pesado": {
                    "nome": "Treino Pesado",
                    "emoji": "🏋️",
                    "nivel_minimo": 20,
                    "cooldown_horas": 20,
                    "min_aumento": 0.4,
                    "max_aumento": 0.6
                },
                "supremo": {
                    "nome": "Treino Supremo",
                    "emoji": "🔥",
                    "nivel_minimo": 50,
                    "cooldown_horas": 24,
                    "min_aumento": 0.7,
                    "max_aumento": 0.7
                }
            },
            "atributos": ["Força", "Defesa", "Velocidade", "Destreza", "Magia", "Sorte"]
        }

CONFIG_TREINO = _carregar_config_treino()


# ==========================================
# OBTER STATUS DO JOGADOR
# ==========================================

def obter_jogador(user_id: int, guild_id: int):
    """Obtém os dados completos do jogador"""
    jogador = jogadores.find_one({
        "ID": str(user_id),
        "guild_id": str(guild_id)
    })
    return jogador


# ==========================================
# VERIFICAR COOLDOWN
# ==========================================

def verificar_cooldown(user_id: int, guild_id: int, tipo_treino: str):
    """Verifica se o jogador pode fazer o treino"""
    jogador = obter_jogador(user_id, guild_id)
    
    if not jogador:
        return {"pode": False, "mensagem": "Jogador não encontrado."}
    
    # Verifica se está morto
    if jogador.get("Situação") == "morto":
        return {"pode": False, "mensagem": "❌ Você está morto. Não pode treinar."}
    
    # Pega a configuração do treino
    treino_config = CONFIG_TREINO["treinos"].get(tipo_treino)
    if not treino_config:
        return {"pode": False, "mensagem": "Tipo de treino inválido."}
    
    # Verifica nível mínimo
    nivel = jogador.get("Nivel", 1)
    if nivel < treino_config["nivel_minimo"]:
        return {
            "pode": False,
            "mensagem": f"❌ Você precisa ser nível **{treino_config['nivel_minimo']}** para fazer {treino_config['nome']}. (Seu nível: {nivel})"
        }
    
    # Verifica cooldown
    ultimo_treino = jogador.get("ultimo_treino", {})
    ultimo_treino_tipo = ultimo_treino.get(tipo_treino)
    
    if ultimo_treino_tipo:
        data_ultimo = datetime.datetime.fromisoformat(ultimo_treino_tipo)
        horas_passadas = (datetime.datetime.utcnow() - data_ultimo).total_seconds() / 3600
        
        if horas_passadas < treino_config["cooldown_horas"]:
            horas_restantes = treino_config["cooldown_horas"] - horas_passadas
            return {
                "pode": False,
                "mensagem": f"⏰ Você já fez {treino_config['nome']} recentemente. Aguarde {int(horas_restantes)} horas."
            }
    
    return {"pode": True}


# ==========================================
# REALIZAR TREINO
# ==========================================

def realizar_treino(user_id: int, guild_id: int, tipo_treino: str):
    """Realiza o treino e aplica os aumentos"""
    jogador = obter_jogador(user_id, guild_id)
    
    if not jogador:
        return {"sucesso": False, "mensagem": "Jogador não encontrado."}
    
    # Verifica se pode treinar
    verificacao = verificar_cooldown(user_id, guild_id, tipo_treino)
    if not verificacao["pode"]:
        return {"sucesso": False, "mensagem": verificacao["mensagem"]}
    
    # Pega a configuração do treino
    treino_config = CONFIG_TREINO["treinos"][tipo_treino]
    atributos = CONFIG_TREINO["atributos"]
    
    # Calcula os aumentos para cada atributo
    aumentos = {}
    for atributo in atributos:
        if treino_config["min_aumento"] == treino_config["max_aumento"]:
            # Caso especial: supremo (valor fixo)
            aumento = treino_config["min_aumento"]
        else:
            aumento = round(random.uniform(
                treino_config["min_aumento"],
                treino_config["max_aumento"]
            ), 2)
        aumentos[atributo] = aumento
    
    # Aplica os aumentos no MongoDB
    update_data = {}
    for atributo, valor in aumentos.items():
        update_data[atributo] = jogador.get(atributo, 0) + valor
    
    # Registra o treino
    ultimo_treino = jogador.get("ultimo_treino", {})
    ultimo_treino[tipo_treino] = datetime.datetime.utcnow().isoformat()
    
    # Atualiza no banco
    resultado = jogadores.update_one(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id)
        },
        {
            "$set": {
                **update_data,
                "ultimo_treino": ultimo_treino
            }
        }
    )
    
    if resultado.modified_count > 0:
        # Busca os novos valores
        jogador_atualizado = obter_jogador(user_id, guild_id)
        
        return {
            "sucesso": True,
            "mensagem": f"✅ {treino_config['emoji']} **{treino_config['nome']}** realizado com sucesso!",
            "aumentos": aumentos,
            "novos_valores": {
                atributo: jogador_atualizado.get(atributo, 0)
                for atributo in atributos
            },
            "cooldown_horas": treino_config["cooldown_horas"]
        }
    
    return {"sucesso": False, "mensagem": "Erro ao realizar treino."}


# ==========================================
# LISTAR TREINOS DISPONÍVEIS
# ==========================================

def listar_treinos_disponiveis(user_id: int, guild_id: int):
    """Lista todos os treinos disponíveis para o jogador"""
    jogador = obter_jogador(user_id, guild_id)
    
    if not jogador:
        return []
    
    nivel = jogador.get("Nivel", 1)
    treinos_disponiveis = []
    
    for tipo, config in CONFIG_TREINO["treinos"].items():
        if nivel >= config["nivel_minimo"]:
            treinos_disponiveis.append({
                "tipo": tipo,
                "nome": config["nome"],
                "emoji": config["emoji"],
                "nivel_minimo": config["nivel_minimo"],
                "cooldown_horas": config["cooldown_horas"],
                "descricao": config.get("descricao", "")
            })
    
    return treinos_disponiveis


# ==========================================
# OBTER TEMPO RESTANTE DO COOLDOWN
# ==========================================

def get_cooldown_restante(user_id: int, guild_id: int, tipo_treino: str):
    """Retorna o tempo restante do cooldown em horas"""
    jogador = obter_jogador(user_id, guild_id)
    
    if not jogador:
        return None
    
    treino_config = CONFIG_TREINO["treinos"].get(tipo_treino)
    if not treino_config:
        return None
    
    ultimo_treino = jogador.get("ultimo_treino", {})
    ultimo_treino_tipo = ultimo_treino.get(tipo_treino)
    
    if not ultimo_treino_tipo:
        return 0
    
    data_ultimo = datetime.datetime.fromisoformat(ultimo_treino_tipo)
    horas_passadas = (datetime.datetime.utcnow() - data_ultimo).total_seconds() / 3600
    horas_restantes = treino_config["cooldown_horas"] - horas_passadas
    
    return max(0, horas_restantes)