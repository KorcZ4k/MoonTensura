from pymongo import ReturnDocument
from database.python.mongodb import db


# ==========================================
# COLLECTION
# ==========================================

# Verifica se o db existe antes de acessar
if db is not None:
    hunos = db["Hunos"]
else:
    hunos = None


# ==========================================
# OBTER SALDO
# ==========================================

def obter_hunos(user_id: int, guild_id: int) -> dict:
    if hunos is None:
        return {"carteira": 0, "banco": 0}

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


def get_hunos(user_id: str, guild_id: str) -> int:
    """Pega apenas o saldo da carteira (para compatibilidade com os comandos)"""
    if hunos is None:
        return 0
    resultado = obter_hunos(int(user_id), int(guild_id))
    return resultado["carteira"]


# ==========================================
# ADICIONAR HUNOS
# ==========================================

def adicionar_hunos(
    user_id: int,
    guild_id: int,
    quantidade: int
):
    if hunos is None:
        raise ValueError("Banco de dados não conectado.")

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


def add_hunos(user_id: str, guild_id: str, quantidade: int) -> bool:
    """Adiciona Hunos (versão simplificada para compatibilidade)"""
    try:
        adicionar_hunos(int(user_id), int(guild_id), quantidade)
        return True
    except Exception as e:
        print(f"❌ Erro ao adicionar Hunos: {e}")
        return False


# ==========================================
# REMOVER HUNOS
# ==========================================

def remover_hunos(
    user_id: int,
    guild_id: int,
    quantidade: int
):
    if hunos is None:
        raise ValueError("Banco de dados não conectado.")

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


def remove_hunos(user_id: str, guild_id: str, quantidade: int) -> bool:
    """Remove Hunos (versão simplificada para compatibilidade)"""
    try:
        remover_hunos(int(user_id), int(guild_id), quantidade)
        return True
    except Exception as e:
        print(f"❌ Erro ao remover Hunos: {e}")
        return False


# ==========================================
# ATUALIZAR HUNOS (CRÉDITO/DÉBITO)
# ==========================================

def atualizar_hunos(
    user_id: str,
    guild_id: str,
    quantidade: int
) -> bool:
    """Atualiza Hunos (positivo = ganho, negativo = perda)"""
    if quantidade > 0:
        return add_hunos(user_id, guild_id, quantidade)
    elif quantidade < 0:
        return remove_hunos(user_id, guild_id, abs(quantidade))
    return True


def update_hunos(user_id: str, guild_id: str, quantidade: int) -> bool:
    """Alias para atualizar_hunos"""
    return atualizar_hunos(user_id, guild_id, quantidade)


# ==========================================
# DEPOSITAR HUNOS
# ==========================================

def depositar_hunos(
    user_id: int,
    guild_id: int,
    quantidade: int
):
    if hunos is None:
        raise ValueError("Banco de dados não conectado.")

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
    if hunos is None:
        raise ValueError("Banco de dados não conectado.")

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
    if hunos is None:
        raise ValueError("Banco de dados não conectado.")

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


def pay_hunos(
    remetente_id: str,
    destinatario_id: str,
    guild_id: str,
    quantidade: int
) -> bool:
    """Paga Hunos de um jogador para outro (versão simplificada)"""
    try:
        pagar_hunos(
            int(remetente_id),
            int(destinatario_id),
            int(guild_id),
            quantidade
        )
        return True
    except Exception as e:
        print(f"❌ Erro ao pagar Hunos: {e}")
        return False


# ==========================================
# RANKING DE HUNOS
# ==========================================

def ranking_hunos(
    guild_id: int,
    limite: int = 10
):
    if hunos is None:
        return []

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
    if hunos is None:
        return {
            "carteira_total": 0,
            "banco_total": 0,
            "total": 0,
            "jogadores": 0
        }

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


# ==========================================
# CRIAR JOGADOR (SE NÃO EXISTIR)
# ==========================================

def criar_jogador(
    user_id: int,
    guild_id: int
):
    """Cria um jogador na coleção Hunos se não existir"""
    if hunos is None:
        return False

    resultado = hunos.update_one(
        {
            "ID": str(user_id),
            "guild_id": str(guild_id)
        },
        {
            "$setOnInsert": {
                "carteira": 0,
                "banco": 0
            }
        },
        upsert=True
    )
    return resultado.upserted_id is not None


# ==========================================
# VERIFICAR SE JOGADOR EXISTE
# ==========================================

def jogador_existe(
    user_id: int,
    guild_id: int
) -> bool:
    """Verifica se o jogador existe na coleção Hunos"""
    if hunos is None:
        return False

    jogador = hunos.find_one({
        "ID": str(user_id),
        "guild_id": str(guild_id)
    })
    return jogador is not None


# ==========================================
# INSTÂNCIA GLOBAL (para compatibilidade)
# ==========================================

class DatabaseHunos:
    """Classe wrapper para compatibilidade com os comandos"""
    
    def __init__(self, database):
        self.db = database
        # Verifica se o db não é None antes de acessar
        if database is not None:
            self.colecao = database["Hunos"]
        else:
            self.colecao = None
    
    def get_hunos(self, user_id: str, guild_id: str) -> int:
        return get_hunos(user_id, guild_id)
    
    def add_hunos(self, user_id: str, guild_id: str, quantidade: int) -> bool:
        return add_hunos(user_id, guild_id, quantidade)
    
    def remove_hunos(self, user_id: str, guild_id: str, quantidade: int) -> bool:
        return remove_hunos(user_id, guild_id, quantidade)
    
    def update_hunos(self, user_id: str, guild_id: str, quantidade: int) -> bool:
        return update_hunos(user_id, guild_id, quantidade)
    
    def pay_hunos(self, remetente_id: str, destinatario_id: str, guild_id: str, quantidade: int) -> bool:
        return pay_hunos(remetente_id, destinatario_id, guild_id, quantidade)


# Instância global
db_hunos = None

def init_db_hunos(database):
    """Inicializa a instância global do DatabaseHunos"""
    global db_hunos
    db_hunos = DatabaseHunos(database)
    return db_hunos