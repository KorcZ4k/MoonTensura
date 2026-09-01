from database.python.mongodb import db
import json
import random
import datetime

# ==========================================
# COLLECTION
# ==========================================

jogadores = db["Jogadores"]


# ==========================================
# MENSAGENS DE MORTE
# ==========================================

def _carregar_mensagens_morte():
    """Carrega as mensagens de morte do JSON"""
    try:
        with open('data/death_messages.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erro ao carregar mensagens de morte: {e}")
        return {
            "humanas": ["{nome} caiu em batalha! Sua alma partiu para sempre."],
            "monstros": ["O monstro {nome} foi derrotado! Sua essência se dissipou."],
            "animados": ["{nome} foi destruído! Sua energia se desfez."]
        }

DEATH_MESSAGES = _carregar_mensagens_morte()


# ==========================================
# OBTER STATUS
# ==========================================

def obter_status(
    user_id: int,
    guild_id: int
):
    jogador = jogadores.find_one({
        "ID": str(user_id),
        "guild_id": str(guild_id)
    })

    if jogador is None:
        return None

    return jogador


# ==========================================
# OBTER ATRIBUTO
# ==========================================

def obter_atributo(
    user_id: int,
    guild_id: int,
    atributo: str
):
    jogador = jogadores.find_one(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id)
        },
        {
            atributo: 1,
            "_id": 0
        }
    )

    if jogador is None:
        return None

    return jogador.get(atributo, 0)


# ==========================================
# ALTERAR ATRIBUTO
# ==========================================

def alterar_atributo(
    user_id: int,
    guild_id: int,
    atributo: str,
    valor: int
):
    atributos_validos = [
        "Força",
        "Defesa",
        "Velocidade",
        "Destreza",
        "Magia",
        "Sorte"
    ]

    if atributo not in atributos_validos:
        raise ValueError(
            "Atributo inválido."
        )

    if valor < 0:
        raise ValueError(
            "O valor não pode ser negativo."
        )

    resultado = jogadores.update_one(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id)
        },
        {
            "$set": {
                atributo: valor
            }
        }
    )

    if resultado.matched_count == 0:
        raise ValueError(
            "Jogador não encontrado."
        )

    return valor


# ==========================================
# AUMENTAR ATRIBUTO
# ==========================================

def aumentar_atributo(
    user_id: int,
    guild_id: int,
    atributo: str,
    quantidade: int
):
    atributos_validos = [
        "Força",
        "Defesa",
        "Velocidade",
        "Destreza",
        "Magia",
        "Sorte"
    ]

    if atributo not in atributos_validos:
        raise ValueError(
            "Atributo inválido."
        )

    if quantidade <= 0:
        raise ValueError(
            "A quantidade deve ser maior que zero."
        )

    resultado = jogadores.find_one_and_update(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id)
        },
        {
            "$inc": {
                atributo: quantidade
            }
        },
        return_document=True
    )

    if resultado is None:
        raise ValueError(
            "Jogador não encontrado."
        )

    return resultado.get(atributo, 0)


# ==========================================
# REDUZIR ATRIBUTO
# ==========================================

def reduzir_atributo(
    user_id: int,
    guild_id: int,
    atributo: str,
    quantidade: int
):
    atributos_validos = [
        "Força",
        "Defesa",
        "Velocidade",
        "Destreza",
        "Magia",
        "Sorte"
    ]

    if atributo not in atributos_validos:
        raise ValueError(
            "Atributo inválido."
        )

    if quantidade <= 0:
        raise ValueError(
            "A quantidade deve ser maior que zero."
        )

    jogador = jogadores.find_one(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id)
        }
    )

    if jogador is None:
        raise ValueError(
            "Jogador não encontrado."
        )

    valor_atual = jogador.get(
        atributo,
        0
    )

    if valor_atual < quantidade:
        raise ValueError(
            "O jogador não possui pontos suficientes."
        )

    resultado = jogadores.find_one_and_update(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id),
            atributo: {
                "$gte": quantidade
            }
        },
        {
            "$inc": {
                atributo: -quantidade
            }
        },
        return_document=True
    )

    if resultado is None:
        raise ValueError(
            "Não foi possível reduzir o atributo."
        )

    return resultado.get(
        atributo,
        0
    )


# ==========================================
# OBTER XP
# ==========================================

def obter_xp(
    user_id: int,
    guild_id: int
):
    jogador = jogadores.find_one(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id)
        },
        {
            "XP": 1,
            "_id": 0
        }
    )

    if jogador is None:
        return None

    return jogador.get(
        "XP",
        0
    )


# ==========================================
# ADICIONAR XP
# ==========================================

def adicionar_xp(
    user_id: int,
    guild_id: int,
    quantidade: int
):
    if quantidade <= 0:
        raise ValueError(
            "A quantidade de XP deve ser maior que zero."
        )

    resultado = jogadores.find_one_and_update(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id)
        },
        {
            "$inc": {
                "XP": quantidade
            }
        },
        return_document=True
    )

    if resultado is None:
        raise ValueError(
            "Jogador não encontrado."
        )

    # Verifica se subiu de nível
    xp_atual = resultado.get("XP", 0)
    nivel_atual = resultado.get("Nivel", 1)
    xp_maximo = 100 * nivel_atual
    
    while xp_atual >= xp_maximo:
        xp_atual -= xp_maximo
        nivel_atual += 1
        xp_maximo = 100 * nivel_atual
        
        jogadores.update_one(
            {
                "ID": str(user_id),
                "guild_id": str(guild_id)
            },
            {
                "$set": {
                    "Nivel": nivel_atual,
                    "XP": xp_atual,
                    "XP_maximo": xp_maximo
                }
            }
        )

    return resultado.get(
        "XP",
        0
    )


# ==========================================
# REMOVER XP
# ==========================================

def remover_xp(
    user_id: int,
    guild_id: int,
    quantidade: int
):
    if quantidade <= 0:
        raise ValueError(
            "A quantidade de XP deve ser maior que zero."
        )

    resultado = jogadores.find_one_and_update(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id),
            "XP": {
                "$gte": quantidade
            }
        },
        {
            "$inc": {
                "XP": -quantidade
            }
        },
        return_document=True
    )

    if resultado is None:
        raise ValueError(
            "XP insuficiente ou jogador não encontrado."
        )

    return resultado.get(
        "XP",
        0
    )


# ==========================================
# ALTERAR NÍVEL
# ==========================================

def alterar_nivel(
    user_id: int,
    guild_id: int,
    nivel: int
):
    if nivel < 0:
        raise ValueError(
            "O nível não pode ser negativo."
        )

    resultado = jogadores.update_one(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id)
        },
        {
            "$set": {
                "Nivel": nivel
            }
        }
    )

    if resultado.matched_count == 0:
        raise ValueError(
            "Jogador não encontrado."
        )

    return nivel


# ==========================================
# ALTERAR NOME
# ==========================================

def alterar_nome(
    user_id: int,
    guild_id: int,
    nome: str
):
    if not nome or not nome.strip():
        raise ValueError(
            "O nome não pode estar vazio."
        )

    resultado = jogadores.update_one(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id)
        },
        {
            "$set": {
                "Nome": nome.strip()
            }
        }
    )

    if resultado.matched_count == 0:
        raise ValueError(
            "Jogador não encontrado."
        )

    return nome.strip()


# ==========================================
# ALTERAR RAÇA
# ==========================================

def alterar_raca(
    user_id: int,
    guild_id: int,
    raca: str
):
    if not raca or not raca.strip():
        raise ValueError(
            "A raça não pode estar vazia."
        )

    resultado = jogadores.update_one(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id)
        },
        {
            "$set": {
                "Raça": raca.strip()
            }
        }
    )

    if resultado.matched_count == 0:
        raise ValueError(
            "Jogador não encontrado."
        )

    return raca.strip()


# ==========================================
# SISTEMA DE MORTE (PERMANENTE)
# ==========================================

def verificar_morte(user_id: int, guild_id: int):
    """Verifica se o jogador morreu e aplica a morte permanente"""
    try:
        jogador = jogadores.find_one({
            "ID": str(user_id),
            "guild_id": str(guild_id)
        })
        
        if not jogador:
            return None
        
        # Verifica se já está morto
        if jogador.get("Situação") == "morto":
            return {
                "morreu": True,
                "ja_estava_morto": True,
                "mensagem": f"{jogador.get('Nome', 'Alguém')} já está morto."
            }
        
        vida = jogador.get("Vida", 0)
        vida_maxima = jogador.get("Vida_Maxima", 100)
        magiculas = jogador.get("Magículas", 0)
        raca = jogador.get("Raça", "Humano")
        
        # Verifica se é monstro
        racas_monstro = ["monstro", "criatura", "bestial", "dragão", "fera", "demônio", "abominação"]
        is_monstro = raca.lower() in racas_monstro
        
        # Verifica se é humano (vida zerada = morte)
        if not is_monstro and vida <= 0:
            return _aplicar_morte_permanente(jogador, user_id, guild_id, "humano")
        
        # Verifica se é monstro (vida ou magículas zerada = morte)
        if is_monstro:
            if vida <= 0:
                return _aplicar_morte_permanente(jogador, user_id, guild_id, "monstro_vida")
            if magiculas <= 0:
                return _aplicar_morte_permanente(jogador, user_id, guild_id, "monstro_magia")
        
        # Verifica se é animado/constructo (vida zerada = morte)
        racas_animadas = ["constructo", "golem", "boneco", "esqueleto", "zumbi", "lorde das trevas"]
        if raca.lower() in racas_animadas and vida <= 0:
            return _aplicar_morte_permanente(jogador, user_id, guild_id, "animado")
        
        return None
        
    except Exception as e:
        print(f"❌ Erro ao verificar morte: {e}")
        return None


def _aplicar_morte_permanente(jogador: dict, user_id: int, guild_id: int, tipo: str):
    """Aplica a morte permanente do jogador"""
    
    # Escolhe uma mensagem aleatória
    if tipo == "humano":
        mensagens = DEATH_MESSAGES.get("humanas", ["{nome} caiu em batalha! Sua alma partiu para sempre."])
    elif tipo in ["monstro_vida", "monstro_magia"]:
        mensagens = DEATH_MESSAGES.get("monstros", ["O monstro {nome} foi derrotado! Sua essência se dissipou."])
    elif tipo == "animado":
        mensagens = DEATH_MESSAGES.get("animados", ["{nome} foi destruído! Sua energia se desfez."])
    else:
        mensagens = ["{nome} morreu permanentemente!"]
    
    nome = jogador.get("Nome", jogador.get("ID", "Alguém"))
    mensagem = random.choice(mensagens).format(nome=nome)
    
    # Atualiza o jogador para "morto"
    resultado = jogadores.update_one(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id)
        },
        {
            "$set": {
                "Situação": "morto",
                "Vida": 0,
                "data_morte": datetime.datetime.utcnow().isoformat(),
                "mensagem_morte": mensagem,
                "tipo_morte": tipo
            }
        }
    )
    
    if resultado.modified_count > 0:
        return {
            "morreu": True,
            "ja_estava_morto": False,
            "mensagem": mensagem,
            "tipo": tipo,
            "data_morte": datetime.datetime.utcnow().isoformat()
        }
    
    return {
        "morreu": False,
        "mensagem": "Erro ao processar a morte."
    }


def reviver(user_id: int, guild_id: int):
    """Revive o jogador (volta à vida com status completo)"""
    try:
        jogador = jogadores.find_one({
            "ID": str(user_id),
            "guild_id": str(guild_id)
        })
        
        if not jogador:
            return {"sucesso": False, "mensagem": "Jogador não encontrado."}
        
        if jogador.get("Situação") != "morto":
            return {"sucesso": False, "mensagem": "Este jogador não está morto."}
        
        # Restaura o jogador
        vida_maxima = jogador.get("Vida_Maxima", 100)
        mana_maxima = jogador.get("Mana Total", 100)
        
        resultado = jogadores.update_one(
            {
                "ID": str(user_id),
                "guild_id": str(guild_id)
            },
            {
                "$set": {
                    "Situação": "ativo",
                    "Vida": vida_maxima,
                    "Mana": mana_maxima,
                    "data_morte": None,
                    "mensagem_morte": None,
                    "tipo_morte": None
                }
            }
        )
        
        if resultado.modified_count > 0:
            return {
                "sucesso": True,
                "mensagem": f"{jogador.get('Nome', 'Alguém')} foi revivido!"
            }
        
        return {"sucesso": False, "mensagem": "Erro ao reviver."}
        
    except Exception as e:
        print(f"❌ Erro ao reviver: {e}")
        return {"sucesso": False, "mensagem": str(e)}


def aplicar_dano(user_id: int, guild_id: int, dano: int, tipo_dano: str = "fisico"):
    """Aplica dano a um jogador e verifica se morreu"""
    try:
        jogador = jogadores.find_one({
            "ID": str(user_id),
            "guild_id": str(guild_id)
        })
        
        if not jogador:
            return {"sucesso": False, "mensagem": "Jogador não encontrado."}
        
        # Verifica se já está morto
        if jogador.get("Situação") == "morto":
            return {
                "sucesso": False,
                "mensagem": f"{jogador.get('Nome', 'Alguém')} já está morto.",
                "ja_morto": True
            }
        
        # Aplica o dano
        vida_atual = jogador.get("Vida", 0)
        defesa = jogador.get("Defesa", 0)
        
        # Reduz o dano baseado na defesa (se for dano físico)
        if tipo_dano == "fisico":
            dano_reduzido = max(1, dano - int(defesa * 0.2))
        else:
            dano_reduzido = dano
        
        nova_vida = max(0, vida_atual - dano_reduzido)
        
        # Atualiza a vida
        jogadores.update_one(
            {
                "ID": str(user_id),
                "guild_id": str(guild_id)
            },
            {
                "$set": {
                    "Vida": nova_vida
                }
            }
        )
        
        # Verifica se morreu
        resultado_morte = verificar_morte(user_id, guild_id)
        
        if resultado_morte and resultado_morte.get("morreu"):
            return {
                "sucesso": True,
                "dano_aplicado": dano_reduzido,
                "vida_restante": 0,
                "morreu": True,
                "mensagem_morte": resultado_morte.get("mensagem", ""),
                "ja_morto": False
            }
        
        return {
            "sucesso": True,
            "dano_aplicado": dano_reduzido,
            "vida_restante": nova_vida,
            "morreu": False,
            "mensagem_morte": None,
            "ja_morto": False
        }
        
    except Exception as e:
        print(f"❌ Erro ao aplicar dano: {e}")
        return {"sucesso": False, "mensagem": str(e)}


def aplicar_cura(user_id: int, guild_id: int, cura: int):
    """Aplica cura a um jogador"""
    try:
        jogador = jogadores.find_one({
            "ID": str(user_id),
            "guild_id": str(guild_id)
        })
        
        if not jogador:
            return {"sucesso": False, "mensagem": "Jogador não encontrado."}
        
        # Verifica se está morto
        if jogador.get("Situação") == "morto":
            return {
                "sucesso": False,
                "mensagem": "Não é possível curar um jogador morto.",
                "ja_morto": True
            }
        
        vida_atual = jogador.get("Vida", 0)
        vida_maxima = jogador.get("Vida_Maxima", 100)
        
        nova_vida = min(vida_maxima, vida_atual + cura)
        
        jogadores.update_one(
            {
                "ID": str(user_id),
                "guild_id": str(guild_id)
            },
            {
                "$set": {
                    "Vida": nova_vida
                }
            }
        )
        
        return {
            "sucesso": True,
            "cura_aplicada": nova_vida - vida_atual,
            "vida_atual": nova_vida,
            "vida_maxima": vida_maxima,
            "ja_morto": False
        }
        
    except Exception as e:
        print(f"❌ Erro ao aplicar cura: {e}")
        return {"sucesso": False, "mensagem": str(e)}


# ==========================================
# RECUPERAR MANA (DESCANSO E MEDITAÇÃO)
# ==========================================

def recuperar_mana(user_id: int, guild_id: int, tipo: str):
    """
    Recupera mana do jogador
    tipo: "descanso" ou "meditacao"
    """
    try:
        jogador = jogadores.find_one({
            "ID": str(user_id),
            "guild_id": str(guild_id)
        })
        
        if not jogador:
            return {"sucesso": False, "mensagem": "Jogador não encontrado."}
        
        # Verifica se está morto
        if jogador.get("Situação") == "morto":
            return {"sucesso": False, "mensagem": "❌ Você está morto. Não pode recuperar mana."}
        
        mana_atual = jogador.get("Mana", 0)
        mana_maxima = jogador.get("Mana Total", 100)
        mana_total = jogador.get("Mana Total", 100)
        
        # Verifica se já está com mana cheia
        if mana_atual >= mana_maxima:
            return {"sucesso": False, "mensagem": "❌ Sua mana já está cheia!"}
        
        # Calcula a recuperação baseada no tipo
        if tipo == "descanso":
            min_recuperacao = 0.10
            max_recuperacao = 0.25
            nome = "Descanso"
            emoji = "🛌"
            cooldown_horas = 6
        elif tipo == "meditacao":
            min_recuperacao = 0.35
            max_recuperacao = 0.50
            nome = "Meditação"
            emoji = "🧘"
            cooldown_horas = 12
        else:
            return {"sucesso": False, "mensagem": "Tipo de recuperação inválido."}
        
        # Verifica cooldown
        ultima_recuperacao = jogador.get("ultima_recuperacao", {})
        ultimo_registro = ultima_recuperacao.get(tipo)
        
        if ultimo_registro:
            data_ultimo = datetime.datetime.fromisoformat(ultimo_registro)
            horas_passadas = (datetime.datetime.utcnow() - data_ultimo).total_seconds() / 3600
            
            if horas_passadas < cooldown_horas:
                horas_restantes = cooldown_horas - horas_passadas
                return {
                    "sucesso": False,
                    "mensagem": f"⏰ Você já usou {nome} recentemente. Aguarde {int(horas_restantes)} horas."
                }
        
        # Calcula a recuperação
        percentual_recuperado = round(random.uniform(min_recuperacao, max_recuperacao), 2)
        mana_recuperada = int(mana_total * percentual_recuperado)
        nova_mana = min(mana_maxima, mana_atual + mana_recuperada)
        mana_real_recuperada = nova_mana - mana_atual
        
        # Atualiza no banco
        ultima_recuperacao[tipo] = datetime.datetime.utcnow().isoformat()
        
        resultado = jogadores.update_one(
            {
                "ID": str(user_id),
                "guild_id": str(guild_id)
            },
            {
                "$set": {
                    "Mana": nova_mana,
                    "ultima_recuperacao": ultima_recuperacao
                }
            }
        )
        
        if resultado.modified_count > 0:
            return {
                "sucesso": True,
                "mensagem": f"{emoji} **{nome}** realizado com sucesso!",
                "mana_recuperada": mana_real_recuperada,
                "mana_atual": nova_mana,
                "mana_maxima": mana_maxima,
                "percentual": percentual_recuperado * 100,
                "cooldown_horas": cooldown_horas
            }
        
        return {"sucesso": False, "mensagem": "Erro ao recuperar mana."}
        
    except Exception as e:
        print(f"❌ Erro ao recuperar mana: {e}")
        return {"sucesso": False, "mensagem": str(e)}


def get_cooldown_recuperacao(user_id: int, guild_id: int, tipo: str):
    """Retorna o tempo restante do cooldown de recuperação em horas"""
    jogador = jogadores.find_one({
        "ID": str(user_id),
        "guild_id": str(guild_id)
    })
    
    if not jogador:
        return None
    
    cooldown_horas = 6 if tipo == "descanso" else 12
    
    ultima_recuperacao = jogador.get("ultima_recuperacao", {})
    ultimo_registro = ultima_recuperacao.get(tipo)
    
    if not ultimo_registro:
        return 0
    
    data_ultimo = datetime.datetime.fromisoformat(ultimo_registro)
    horas_passadas = (datetime.datetime.utcnow() - data_ultimo).total_seconds() / 3600
    horas_restantes = cooldown_horas - horas_passadas
    
    return max(0, horas_restantes)


def esta_morto(user_id: int, guild_id: int):
    """Verifica se o jogador está morto"""
    try:
        jogador = jogadores.find_one({
            "ID": str(user_id),
            "guild_id": str(guild_id)
        })
        
        if not jogador:
            return False
        
        return jogador.get("Situação") == "morto"
        
    except Exception as e:
        print(f"❌ Erro ao verificar morte: {e}")
        return False


def get_info_morte(user_id: int, guild_id: int):
    """Retorna informações sobre a morte do jogador"""
    try:
        jogador = jogadores.find_one({
            "ID": str(user_id),
            "guild_id": str(guild_id)
        })
        
        if not jogador:
            return None
        
        if jogador.get("Situação") != "morto":
            return None
        
        return {
            "data_morte": jogador.get("data_morte"),
            "mensagem_morte": jogador.get("mensagem_morte"),
            "tipo_morte": jogador.get("tipo_morte")
        }
        
    except Exception as e:
        print(f"❌ Erro ao buscar info morte: {e}")
        return None


def deletar_personagem_morto(user_id: int, guild_id: int):
    """Deleta permanentemente um personagem morto (opcional)"""
    try:
        jogador = jogadores.find_one({
            "ID": str(user_id),
            "guild_id": str(guild_id)
        })
        
        if not jogador:
            return {"sucesso": False, "mensagem": "Jogador não encontrado."}
        
        if jogador.get("Situação") != "morto":
            return {"sucesso": False, "mensagem": "Este jogador não está morto."}
        
        resultado = jogadores.delete_one({
            "ID": str(user_id),
            "guild_id": str(guild_id)
        })
        
        if resultado.deleted_count > 0:
            return {
                "sucesso": True,
                "mensagem": f"Personagem {jogador.get('Nome', 'Alguém')} foi deletado permanentemente."
            }
        
        return {"sucesso": False, "mensagem": "Erro ao deletar personagem."}
        
    except Exception as e:
        print(f"❌ Erro ao deletar personagem: {e}")
        return {"sucesso": False, "mensagem": str(e)}