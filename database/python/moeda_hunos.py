"""Padrão monetário oficial da economia: Hunos.

A unidade de armazenamento é o Huno de Bronze. Os campos antigos com
sufixo _bronze permanecem como compatibilidade de banco e representam Hunos.
"""

FATOR_PRATA = 100
FATOR_OURO = 10_000
FATOR_ESTELAR = 1_000_000

UNIDADES = (
    ("estelar", "✨ Hunos Estelares", FATOR_ESTELAR),
    ("ouro", "🟡 Hunos de Ouro", FATOR_OURO),
    ("prata", "⚪ Hunos de Prata", FATOR_PRATA),
    ("bronze", "🟤 Hunos de Bronze", 1),
)


def normalizar_hunos(valor):
    try:
        return max(0, int(round(float(valor))))
    except (TypeError, ValueError):
        return 0


def decompor_hunos(valor):
    restante = normalizar_hunos(valor)
    resultado = {"bronze_total": restante, "estelar": 0, "ouro": 0, "prata": 0, "bronze": 0}
    for chave, _, fator in UNIDADES:
        quantidade, restante = divmod(restante, fator)
        resultado[chave] = quantidade
    return resultado


def formatar_hunos(valor, detalhado=True):
    dados = decompor_hunos(valor)
    if not detalhado:
        return f"{dados['bronze_total']:,} Hunos"
    partes = []
    for chave, nome, _ in UNIDADES:
        quantidade = dados[chave]
        if quantidade:
            partes.append(f"{quantidade:,} {nome}")
    return " | ".join(partes) if partes else "0 🟤 Hunos de Bronze"


def campo_hunos(nome):
    """Retorna o nome legado compatível do campo monetário."""
    return f"{nome}_bronze"
