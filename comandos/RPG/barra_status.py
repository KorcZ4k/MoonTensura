def barra_status(atual, maximo, tamanho=15):
    if maximo <= 0:
        return "░" * tamanho

    atual = max(0, min(atual, maximo))

    preenchido = int((atual / maximo) * tamanho)
    vazio = tamanho - preenchido

    return "█" * preenchido + "░" * vazio


def barra_vida(vida, vida_maxima):
    return barra_status(vida, vida_maxima)


def barra_mana(mana, mana_maxima):
    return barra_status(mana, mana_maxima)