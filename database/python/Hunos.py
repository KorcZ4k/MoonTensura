from pymongo import ReturnDocument
from database.python.mongodb import db


# ==========================================
# COLLECTION
# ==========================================

hunos = db["Hunos"]


# ==========================================
# OBTER SALDO
# ==========================================

def obter_hunos(user_id: int, guild_id: int) -> dict:

    jogador = hunos.find_one({
        "ID": str(user_id),
        "guild_id": str(guild_id)
    })

    if jogador is None:
        return {
            "carteira": 0,
            "banco": 0
        }

    return {
        "carteira": jogador.get("carteira", 0),
        "banco": jogador.get("banco", 0)
    }


# ==========================================
# ADICIONAR HUNOS
# ==========================================

def adicionar_hunos(
    user_id: int,
    guild_id: int,
    quantidade: int
):

    if quantidade <= 0:
        raise ValueError(
            "A quantidade deve ser maior que zero."
        )

    resultado = hunos.find_one_and_update(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id)
        },
        {
            "$inc": {
                "carteira": quantidade
            }
        },
        return_document=ReturnDocument.AFTER
    )

    if resultado is None:
        raise ValueError(
            "Jogador não encontrado."
        )

    return resultado["carteira"]


# ==========================================
# REMOVER HUNOS
# ==========================================

def remover_hunos(
    user_id: int,
    guild_id: int,
    quantidade: int
):

    if quantidade <= 0:
        raise ValueError(
            "A quantidade deve ser maior que zero."
        )

    resultado = hunos.find_one_and_update(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id),
            "carteira": {
                "$gte": quantidade
            }
        },
        {
            "$inc": {
                "carteira": -quantidade
            }
        },
        return_document=ReturnDocument.AFTER
    )

    if resultado is None:
        raise ValueError(
            "Hunos insuficientes."
        )

    return resultado["carteira"]


# ==========================================
# DEPOSITAR HUNOS
# ==========================================

def depositar_hunos(
    user_id: int,
    guild_id: int,
    quantidade: int
):

    if quantidade <= 0:
        raise ValueError(
            "A quantidade deve ser maior que zero."
        )

    resultado = hunos.find_one_and_update(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id),
            "carteira": {
                "$gte": quantidade
            }
        },
        {
            "$inc": {
                "carteira": -quantidade,
                "banco": quantidade
            }
        },
        return_document=ReturnDocument.AFTER
    )

    if resultado is None:
        raise ValueError(
            "Hunos insuficientes na carteira."
        )

    return {
        "carteira": resultado["carteira"],
        "banco": resultado["banco"]
    }


# ==========================================
# SACAR HUNOS
# ==========================================

def sacar_hunos(
    user_id: int,
    guild_id: int,
    quantidade: int
):

    if quantidade <= 0:
        raise ValueError(
            "A quantidade deve ser maior que zero."
        )

    resultado = hunos.find_one_and_update(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id),
            "banco": {
                "$gte": quantidade
            }
        },
        {
            "$inc": {
                "banco": -quantidade,
                "carteira": quantidade
            }
        },
        return_document=ReturnDocument.AFTER
    )

    if resultado is None:
        raise ValueError(
            "Hunos insuficientes no banco."
        )

    return {
        "carteira": resultado["carteira"],
        "banco": resultado["banco"]
    }


# ==========================================
# PAGAR HUNOS
# ==========================================

def pagar_hunos(
    remetente_id: int,
    destinatario_id: int,
    guild_id: int,
    quantidade: int
):

    if quantidade <= 0:
        raise ValueError(
            "A quantidade deve ser maior que zero."
        )

    if remetente_id == destinatario_id:
        raise ValueError(
            "Você não pode pagar a si mesmo."
        )

    resultado = hunos.update_one(
        {
            "ID": str(remetente_id),
            "guild_id": str(guild_id),
            "carteira": {
                "$gte": quantidade
            }
        },
        {
            "$inc": {
                "carteira": -quantidade
            }
        }
    )

    if resultado.modified_count == 0:
        raise ValueError(
            "Hunos insuficientes."
        )

    hunos.update_one(
        {
            "ID": str(destinatario_id),
            "guild_id": str(guild_id)
        },
        {
            "$inc": {
                "carteira": quantidade
            }
        },
        upsert=True
    )

    return True


# ==========================================
# RANKING DE HUNOS
# ==========================================

def ranking_hunos(
    guild_id: int,
    limite: int = 10
):

    jogadores = hunos.find(
        {
            "guild_id": str(guild_id)
        }
    ).sort(
        [
            ("carteira", -1),
            ("banco", -1)
        ]
    ).limit(limite)

    return list(jogadores)


# ==========================================
# ECONOMIA DOS HUNOS
# ==========================================

def economia_hunos(
    guild_id: int
):

    resultado = hunos.aggregate([
        {
            "$match": {
                "guild_id": str(guild_id)
            }
        },
        {
            "$group": {
                "_id": None,

                "carteira_total": {
                    "$sum": "$carteira"
                },

                "banco_total": {
                    "$sum": "$banco"
                },

                "jogadores": {
                    "$sum": 1
                }
            }
        }
    ])

    resultado = list(resultado)

    if not resultado:
        return {
            "carteira_total": 0,
            "banco_total": 0,
            "total": 0,
            "jogadores": 0
        }

    dados = resultado[0]

    carteira_total = dados.get(
        "carteira_total",
        0
    )

    banco_total = dados.get(
        "banco_total",
        0
    )

    return {
        "carteira_total": carteira_total,
        "banco_total": banco_total,
        "total": carteira_total + banco_total,
        "jogadores": dados.get(
            "jogadores",
            0
        )
    }
