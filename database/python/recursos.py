from datetime import datetime, timezone


RECURSOS_PADRAO = {
    "construcao": [
        "madeira", "pedra", "areia", "argila", "tijolos", "cimento", "cal", "vidro",
    ],
    "metais": [
        "ferro", "metal", "aco", "cobre", "bronze", "prata", "ouro", "aluminio", "carvao",
    ],
    "alimentos": [
        "carne", "peixe", "graos", "trigo", "arroz", "milho", "batata", "frutas", "vegetais", "sal", "acucar",
    ],
    "animais": [
        "gado", "ovelhas", "cabras", "porcos", "cavalos", "aves",
    ],
    "produtos": [
        "couro", "la", "tecido", "madeira_processada", "tijolo_processado", "ferramentas", "armas", "armaduras",
    ],
    "energia_e_combustivel": [
        "lenha", "carvao_vegetal", "carvao_mineral", "petroleo", "gas", "energia",
    ],
    "naturais": [
        "agua", "terra_fertil", "ervas", "plantas_medicinais", "oleos", "corantes",
    ],
}


def todos_os_recursos():
    return [recurso for categoria in RECURSOS_PADRAO.values() for recurso in categoria]


def criar_recursos_iniciais(db, governo_id, guild_id, owner_id=None, tipo="reino"):
    collection = db["Recursos"]
    agora = datetime.now(timezone.utc)
    documento = collection.find_one({"governo_id": str(governo_id)})
    if documento:
        return documento

    estoque = {recurso: 0.0 for recurso in todos_os_recursos()}
    novo = {
        "governo_id": str(governo_id),
        "guild_id": str(guild_id),
        "owner_id": str(owner_id) if owner_id is not None else None,
        "tipo": tipo,
        "estoque": estoque,
        "capacidade": {},
        "atualizado_em": agora,
        "criado_em": agora,
    }
    collection.insert_one(novo)
    return novo


def obter_recursos(db, governo_id):
    return db["Recursos"].find_one({"governo_id": str(governo_id)})
