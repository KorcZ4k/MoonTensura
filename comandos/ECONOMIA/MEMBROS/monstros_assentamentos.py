import json
import random
from pathlib import Path
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parents[3]
RACAS_PATH = BASE_DIR / "database" / "json" / "racas.json"
MONSTROS_PATH = BASE_DIR / "database" / "json" / "monstros.json"


def _carregar(path):
    with open(path, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def nivel_monstro_por_assentamento(nivel_assentamento: int) -> int:
    nivel_assentamento = max(1, int(nivel_assentamento))
    return 1 if nivel_assentamento <= 2 else nivel_assentamento - 1


def _raca_valida_para_nivel(raca, nivel):
    # Raças extremamente raras ainda podem aparecer, mas respeitam sua chance.
    return float(raca.get("chance", 0)) > 0 and nivel >= 1


def escolher_raca_monstro(nivel: int):
    racas = _carregar(RACAS_PATH).get("racas", [])
    candidatas = [r for r in racas if _raca_valida_para_nivel(r, nivel)]
    if not candidatas:
        return None
    return random.choices(candidatas, weights=[max(0.001, float(r.get("chance", 1))) for r in candidatas], k=1)[0]


def escolher_monstro_base(nivel: int):
    monstros = _carregar(MONSTROS_PATH).get("monstros", {})
    candidatas = [
        (chave, dados) for chave, dados in monstros.items()
        if int(dados.get("nivel_minimo", 1)) <= nivel <= int(dados.get("nivel_maximo", nivel))
    ]
    if not candidatas:
        candidatas = list(monstros.items())
    return random.choice(candidatas) if candidatas else (None, None)


def gerar_monstro_hostil(nivel_assentamento: int):
    nivel = nivel_monstro_por_assentamento(nivel_assentamento)
    raca = escolher_raca_monstro(nivel)
    chave, base = escolher_monstro_base(nivel)

    if not raca and not base:
        return None

    bonus = (raca or {}).get("bonus", {})
    atributos_base = (base or {}).get("atributos_base", {})
    atributos = {}
    for atributo in ["Força", "Defesa", "Velocidade", "Destreza", "Magia", "Sorte"]:
        valor_base = float(atributos_base.get(atributo, 10))
        bonus_raca = float(bonus.get(atributo, 0))
        atributos[atributo.lower().replace("ç", "c")] = max(1, round(valor_base * nivel * (1 + bonus_raca)))

    vida_base = float((base or {}).get("vida_base", 100))
    dano_base = float((base or {}).get("dano_base", 10))
    xp_base = int((base or {}).get("xp_recompensa", 20))
    hunos_base = int((base or {}).get("hunos_recompensa", 20))

    return {
        "id": f"mon-{uuid4().hex[:10]}",
        "tipo": "monstro_hostil",
        "nivel": nivel,
        "raca": (raca or {}).get("nome", (base or {}).get("nome", "Monstro")),
        "monstro_base": chave,
        "nome": (base or {}).get("nome", (raca or {}).get("nome", "Monstro")),
        "emoji": (base or {}).get("emoji", "👹"),
        "vida": max(1, round(vida_base * nivel)),
        "vida_maxima": max(1, round(vida_base * nivel)),
        "dano": max(1, round(dano_base * nivel)),
        "atributos": atributos,
        "habilidades": [],
        "magias": [],
        "recompensas": {
            "xp_jogador": max(1, xp_base * nivel),
            "xp_assentamento": max(1, nivel),
            "hunos": max(0, hunos_base * nivel)
        }
    }
