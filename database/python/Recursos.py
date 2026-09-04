from datetime import datetime, timezone


COLLECTION_RECURSOS = "Recursos"


# Recursos-base de um assentamento/reino. Todos começam em 0 e são
# separados por categorias para permitir produção, comércio e consumo futuros.
CATEGORIAS_RECURSOS = {
    "construcao": [
        "madeira", "pedras", "tijolos", "argila", "cimento", "areia",
        "cascalho", "cal", "vidro", "asfalto", "madeira_tratada",
    ],
    "minerios_e_materiais": [
        "ferro", "metal", "aco", "cobre", "estanho", "bronze", "prata",
        "ouro", "carvao", "carvao_vegetal", "enxofre", "sal", "cristais",
    ],
    "alimentos": [
        "carne", "peixe", "graos", "trigo", "arroz", "milho", "vegetais",
        "frutas", "leite", "ovos", "queijo", "farinha", "pao", "sal_alimentar",
        "agua", "mel", "acucar", "oleo",
    ],
    "agricultura_e_natureza": [
        "sementes", "madeira_bruta", "fibra_vegetal", "couro", "lã",
        "algodao", "seda", "ervas", "plantas_medicinais", "fertilizante",
    ],
    "combustiveis_e_energia": [
        "lenha", "carvao_combustivel", "oleo_combustivel", "gas",
    ],
    "industria_e_artesanato": [
        "tecido", "couro_tratado", "papel", "tinta", "corda", "ceramica",
        "ferramentas", "pregos", "pecas_metalicas",
    ],
    "militar": [
        "madeira_militar", "metal_militar", "aco_militar", "armas", "armaduras",
        "flechas", "escudos", "suprimentos_militares",
    ],
    "especiais": [
        "magisteel", "magiscule_cristalizada", "materiais_magicos", "nucleos_magicos",
    ],
}


def recursos_padrao():
    return {
        recurso: 0.0
        for recursos in CATEGORIAS_RECURSOS.values()
        for recurso in recursos
    }


def criar_recursos(db, *, guild_id, owner_id, assentamento_id=None, reino_id=None):
    """Cria o estoque de recursos sem sobrescrever um estoque existente."""
    collection = db[COLLECTION_RECURSOS]
    filtro = {
        "guild_id": str(guild_id),
        "owner_id": str(owner_id),
        "assentamento_id": str(assentamento_id) if assentamento_id else None,
        "reino_id": str(reino_id) if reino_id else None,
    }

    existente = collection.find_one(filtro)
    if existente:
        return existente

    agora = datetime.now(timezone.utc)
    documento = {
        **filtro,
        "recursos": recursos_padrao(),
        "categorias": CATEGORIAS_RECURSOS,
        "criado_em": agora,
        "atualizado_em": agora,
    }
    resultado = collection.insert_one(documento)
    documento["_id"] = resultado.inserted_id
    return documento
