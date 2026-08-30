from database.python.mongodb  import db

# ==========================================
# COLLECTION
# ==========================================

jogadores = db["Jogadores"]


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