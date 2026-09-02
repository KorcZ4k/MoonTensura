from database.python.mongodb import db
import json
import random


# ==========================================
# CARREGAR CONFIGURAÇÕES
# ==========================================

def _carregar_golpes():
    try:
        with open(
            "database/json/golpes.json",
            "r",
            encoding="utf-8"
        ) as arquivo:
            return json.load(arquivo).get("golpes", {})
    except Exception as erro:
        print(f"Erro ao carregar golpes.json: {erro}")
        return {}


def _carregar_monstros():
    try:
        with open(
            "database/json/monstros.json",
            "r",
            encoding="utf-8"
        ) as arquivo:
            return json.load(arquivo).get("monstros", {})
    except Exception as erro:
        print(f"Erro ao carregar monstros.json: {erro}")
        return {}


GOLPES = _carregar_golpes()
MONSTROS = _carregar_monstros()


# ==========================================
# OBTER JOGADOR
# ==========================================

def obter_jogador(user_id: str, guild_id: str):
    return db["Jogadores"].find_one({
        "ID": str(user_id),
        "guild_id": str(guild_id)
    })


# ==========================================
# CRIAR PARTICIPANTE JOGADOR
# ==========================================

def criar_participante_jogador(user_id: str, guild_id: str):

    jogador = obter_jogador(user_id, guild_id)

    if not jogador:
        return None

    forca = jogador.get("Força", 10)
    defesa = jogador.get("Defesa", 10)

    # Defesa base usada no cálculo de dano
    defesa_total = (forca + defesa) * 2

    return {
        "id": str(user_id),

        "nome": jogador.get(
            "Nome",
            f"Jogador_{user_id}"
        ),

        "tipo": "jogador",

        "vida": jogador.get("Vida", 100),
        "vida_maxima": jogador.get(
            "Vida_Maxima",
            jogador.get("Vida", 100)
        ),

        "mana": jogador.get("Mana", 50),

        "velocidade": jogador.get(
            "Velocidade",
            50
        ),

        "Força": forca,

        "Destreza": jogador.get(
            "Destreza",
            10
        ),

        "defesa": defesa_total,

        # Estados temporários de combate
        "defesa_ativa": False,
        "esquiva_ativa": False
    }


# ==========================================
# CRIAR MONSTRO
# ==========================================

def criar_monstro(tipo: str, nivel: int = 1):

    dados = MONSTROS.get(tipo)

    if not dados:
        return None

    nivel_minimo = dados.get(
        "nivel_minimo",
        1
    )

    nivel_maximo = dados.get(
        "nivel_maximo",
        99
    )

    # Limita o nível
    nivel = max(
        nivel_minimo,
        min(nivel, nivel_maximo)
    )

    # Escala dos atributos
    fator_escala = 1 + (
        (nivel - 1) * 0.75
    )

    atributos_base = dados.get(
        "atributos_base",
        {}
    )

    forca = int(
        atributos_base.get(
            "Força",
            10
        ) * fator_escala
    )

    defesa_base = int(
        atributos_base.get(
            "Defesa",
            10
        ) * fator_escala
    )

    velocidade = int(
        atributos_base.get(
            "Velocidade",
            20
        ) * fator_escala
    )

    destreza = int(
        atributos_base.get(
            "Destreza",
            10
        ) * fator_escala
    )

    # Defesa usada pelo sistema de dano
    defesa_total = (
        forca + defesa_base
    ) * 2

    vida_base = dados.get(
        "vida_base",
        50
    )

    vida = int(
        vida_base * fator_escala
    )

    dano_base = int(
        dados.get(
            "dano_base",
            10
        ) * fator_escala
    )

    xp_recompensa = int(
        dados.get(
            "xp_recompensa",
            20
        ) * fator_escala
    )

    hunos_recompensa = int(
        dados.get(
            "hunos_recompensa",
            10
        ) * fator_escala
    )

    return {

        "id": str(tipo),

        "nome": dados.get(
            "nome",
            tipo
        ),

        "emoji": dados.get(
            "emoji",
            "👹"
        ),

        "tipo": "monstro",

        "nivel": nivel,

        "nivel_minimo": nivel_minimo,
        "nivel_maximo": nivel_maximo,

        "vida": vida,
        "vida_maxima": vida,

        "mana": 0,

        "Força": forca,
        "Destreza": destreza,

        "defesa": defesa_total,

        "velocidade": velocidade,

        "dano_base": dano_base,

        "xp_recompensa": xp_recompensa,
        "hunos_recompensa": hunos_recompensa,

        # O monstro NÃO começa defendendo.
        # Esses estados serão ativados quando
        # ele escolher uma ação defensiva.
        "defesa_ativa": False,
        "esquiva_ativa": False
    }


# ==========================================
# ATIVAR DEFESA
# ==========================================

def ativar_defesa(participante):

    participante["defesa_ativa"] = True
    participante["esquiva_ativa"] = False


# ==========================================
# ATIVAR ESQUIVA
# ==========================================

def ativar_esquiva(participante):

    participante["esquiva_ativa"] = True
    participante["defesa_ativa"] = False


# ==========================================
# LIMPAR ESTADOS DEFENSIVOS
# ==========================================

def limpar_defesa(participante):

    participante["defesa_ativa"] = False
    participante["esquiva_ativa"] = False


# ==========================================
# CALCULAR DANO
# ==========================================

def calcular_dano(atacante, defensor=None):

    # --------------------------------------
    # ESQUIVA
    # --------------------------------------

    if defensor:

        if defensor.get(
            "esquiva_ativa",
            False
        ):

            # Chance base de 40%
            chance_esquiva = 0.40

            if random.random() < chance_esquiva:

                # A esquiva é consumida
                defensor["esquiva_ativa"] = False

                return 0, "esquivou"

            # Falhou, então também é consumida
            defensor["esquiva_ativa"] = False

    # --------------------------------------
    # DEFESA
    # --------------------------------------

    reducao = 0

    if defensor:

        if defensor.get(
            "defesa_ativa",
            False
        ):

            # Defesa reduz 50% do dano
            reducao = 0.50

            # Defesa é consumida
            defensor["defesa_ativa"] = False

    # --------------------------------------
    # DANO BASE
    # --------------------------------------

    if atacante.get("tipo") == "jogador":

        forca = atacante.get(
            "Força",
            10
        )

        destreza = atacante.get(
            "Destreza",
            10
        )

        dano = int(
            (forca + destreza) / 2
        )

        dano += random.randint(
            1,
            10
        )

    else:

        dano = atacante.get(
            "dano_base",
            10
        )

        dano += random.randint(
            1,
            15
        )

    # --------------------------------------
    # DEFESA BASE
    # --------------------------------------

    if defensor:

        defesa = defensor.get(
            "defesa",
            0
        )

        dano = max(
            1,
            dano - int(defesa * 0.1)
        )

    # --------------------------------------
    # DEFESA ATIVA
    # --------------------------------------

    if reducao > 0:

        dano = int(
            dano * (1 - reducao)
        )

    dano = max(
        1,
        dano
    )

    return dano, "normal"


# ==========================================
# APLICAR DANO
# ==========================================

def aplicar_dano(defensor, dano):

    vida_atual = defensor.get(
        "vida",
        0
    )

    defensor["vida"] = max(
        0,
        vida_atual - dano
    )

    return defensor["vida"]


# ==========================================
# VERIFICAR SE PARTICIPANTE ESTÁ VIVO
# ==========================================

def esta_vivo(participante):

    return participante.get(
        "vida",
        0
    ) > 0


# ==========================================
# VERIFICAR SE PODE LUTAR
# ==========================================

def pode_lutar(user_id: str, guild_id: str):

    jogador = obter_jogador(
        user_id,
        guild_id
    )

    if not jogador:

        return {
            "pode": False,
            "mensagem": "Jogador não encontrado."
        }

    if jogador.get(
        "Situação"
    ) == "morto":

        return {
            "pode": False,
            "mensagem": "❌ Você está morto."
        }

    if jogador.get(
        "Situação"
    ) == "ativo_combate":

        return {
            "pode": False,
            "mensagem": (
                "❌ Você já está em combate."
            )
        }

    if jogador.get(
        "Vida",
        0
    ) <= 0:

        return {
            "pode": False,
            "mensagem": (
                "❌ Você está sem vida."
            )
        }

    return {
        "pode": True,
        "mensagem": "Pode lutar."
    }


# ==========================================
# OBTER VENCEDORES
# ==========================================

def obter_vencedores(combate):

    participantes = combate.get(
        "participantes",
        []
    )

    # ------------------------------------------
    # VERIFICA SE ALGUÉM FOI DERROTADO
    # ------------------------------------------

    derrotados = []

    for participante in participantes:

        vida = participante.get(
            "vida",
            0
        )

        if vida <= 0:

            derrotados.append(
                participante
            )

    # ------------------------------------------
    # NINGUÉM FOI DERROTADO
    # ------------------------------------------

    if not derrotados:

        return None

    # ------------------------------------------
    # PVP
    # ------------------------------------------

    if combate.get("pvp", False):

        for participante in participantes:

            if participante.get(
                "vida",
                0
            ) > 0:

                return {
                    "tipo": "vitoria",
                    "vencedor": participante
                }

        return {
            "tipo": "empate",
            "vencedor": None
        }

    # ------------------------------------------
    # PVE
    # ------------------------------------------

    jogador_vivo = False
    monstro_vivo = False

    for participante in participantes:

        if participante.get(
            "vida",
            0
        ) <= 0:

            continue

        if participante.get(
            "tipo"
        ) == "jogador":

            jogador_vivo = True

        elif participante.get(
            "tipo"
        ) == "monstro":

            monstro_vivo = True

    if jogador_vivo and not monstro_vivo:

        return {
            "tipo": "vitoria",
            "lado": "jogadores"
        }

    if monstro_vivo and not jogador_vivo:

        return {
            "tipo": "vitoria",
            "lado": "monstros"
        }

    return {
        "tipo": "empate"
    }


# ==========================================
# FINALIZAR COMBATE
# ==========================================

def finalizar_combate(combate):

    guild_id = combate["guild_id"]

    participantes = combate.get(
        "participantes",
        []
    )

    # --------------------------------------
    # ATUALIZAR JOGADORES
    # --------------------------------------

    for participante in participantes:

        if participante.get("tipo") != "jogador":
            continue

        vida = max(
            0,
            participante.get(
                "vida",
                0
            )
        )

        mana = participante.get(
            "mana",
            0
        )

        situacao = (
            "ativo"
            if vida > 0
            else "morto"
        )

        db["Jogadores"].update_one(

            {
                "ID": participante["id"],
                "guild_id": guild_id
            },

            {
                "$set": {

                    "Situação": situacao,

                    "Vida": vida,

                    "Mana": mana
                }
            }
        )

    # --------------------------------------
    # COMBATE PVP
    # --------------------------------------

    if combate.get(
        "pvp",
        False
    ):

        return None

    # --------------------------------------
    # VERIFICA VITÓRIA
    # --------------------------------------

    resultado = obter_vencedores(
        combate
    )

    if resultado != "jogadores":

        return None

    jogadores_vivos = [

        participante

        for participante in participantes

        if (
            participante.get("tipo")
            == "jogador"

            and participante.get(
                "vida",
                0
            ) > 0
        )
    ]

    monstros_derrotados = [

        participante

        for participante in participantes

        if (
            participante.get("tipo")
            == "monstro"

            and participante.get(
                "vida",
                0
            ) <= 0
        )
    ]

    if not jogadores_vivos:

        return None

    if not monstros_derrotados:

        return None

    # --------------------------------------
    # CALCULAR RECOMPENSAS
    # --------------------------------------

    xp_total = sum(

        monstro.get(
            "xp_recompensa",
            0
        )

        for monstro
        in monstros_derrotados
    )

    hunos_total = sum(

        monstro.get(
            "hunos_recompensa",
            0
        )

        for monstro
        in monstros_derrotados
    )

# --------------------------------------
# ENTREGAR RECOMPENSAS
# --------------------------------------

    for jogador in jogadores_vivos:

    # Adiciona XP ao jogador
        db["Jogadores"].update_one(
        {
            "ID": str(jogador["id"]),
            "guild_id": str(guild_id)
        },
        {
            "$inc": {
                "XP": int(xp_total)
            }
        }
    )

    # Adiciona Hunos ao jogador
        db["Hunos"].update_one(
        {
            "ID": str(jogador["id"]),
            "guild_id": str(guild_id)
        },
        {
            "$inc": {
                "carteira": int(hunos_total)
            }
        },
        upsert=True
    )


        return {
    "xp": int(xp_total),
    "hunos": int(hunos_total)
}