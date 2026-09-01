def barra_status(atual, maximo, tamanho=15, bloco="⬜"):
    if maximo <= 0:
        return bloco * tamanho

    atual = max(0, min(atual, maximo))

    preenchido = int((atual / maximo) * tamanho)
    vazio = tamanho - preenchido

    return bloco * preenchido + "⬜" * vazio


def barra_vida(vida, vida_maxima):
    return barra_status(
        vida,
        vida_maxima,
        bloco="🟥"
    )


def barra_mana(mana, mana_maxima):
    return barra_status(
        mana,
        mana_maxima,
        bloco="🟦"
    )

def barra_xp(xp, xp_maximo):
    return barra_status(
        xp,
        xp_maximo,
        bloco="🟨"
    )