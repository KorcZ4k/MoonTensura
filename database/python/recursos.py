from datetime import datetime, timezone


# Catálogo global de recursos do sistema econômico.
RECURSOS_PADRAO = {
    "construcao": [
        "madeira", "pedra", "areia", "argila", "tijolos", "cimento", "cal", "cascalho",
        "vidro", "ceramica", "telhas", "madeira_processada", "aco_reforcado",
    ],
    "minerios_e_metais": [
        "ferro", "metal", "aco", "cobre", "bronze", "estanho", "chumbo", "zinco",
        "aluminio", "niquel", "cromo", "manganes", "prata", "ouro", "platina",
    ],
    "alimentos": [
        "carne", "peixe", "leite", "ovos", "graos", "trigo", "arroz", "milho",
        "batata", "frutas", "vegetais", "sal", "acucar", "farinha", "oleos",
    ],
    "animais": [
        "gado", "ovelhas", "cabras", "porcos", "cavalos", "aves", "animais_de_carga",
    ],
    "produtos_e_materiais": [
        "couro", "la", "algodao", "tecido", "papel", "borracha", "plastico",
        "ferramentas", "pecas", "corda", "tinta",
    ],
    "energia_e_combustivel": [
        "lenha", "carvao_vegetal", "carvao_mineral", "petroleo", "gas", "combustivel",
    ],
    "naturais": [
        "agua", "terra_fertil", "sementes", "ervas", "plantas_medicinais", "madeira_agricola",
        "corantes", "enxofre",
    ],
    "industriais_e_militares": [
        "armas", "armaduras", "escudos", "equipamento_militar", "ferramentas_industriais",
    ],
    "especiais": [
        "cristais", "materiais_magicos", "nucleos_magicos", "medicamentos",
    ],
}


def todos_os_recursos():
    return sorted({recurso for categoria in RECURSOS_PADRAO.values() for recurso in categoria})


def criar_recursos_iniciais(db, governo_id, guild_id, owner_id=None, tipo="reino"):
    """Cria um estoque de recursos sem substituir um estoque já existente."""
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
