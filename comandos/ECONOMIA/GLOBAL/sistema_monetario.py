from decimal import Decimal, ROUND_HALF_UP


class SistemaMonetarioHunos:
    """Etapa 15: unidade monetária padronizada da economia global."""

    UNIDADES = {
        "bronze": Decimal("1"),
        "prata": Decimal("100"),
        "ouro": Decimal("10000"),
        "estelar": Decimal("1000000"),
    }

    ORDEM = ("estelar", "ouro", "prata", "bronze")

    @classmethod
    def _valor(cls, valor):
        try:
            return max(Decimal("0"), Decimal(str(valor)))
        except Exception:
            return Decimal("0")

    @classmethod
    def para_unidade_base(cls, valor, unidade="bronze"):
        unidade = str(unidade or "bronze").lower()
        if unidade not in cls.UNIDADES:
            raise ValueError(f"Unidade monetária inválida: {unidade}")
        return cls._valor(valor) * cls.UNIDADES[unidade]

    @classmethod
    def converter(cls, valor, origem="bronze", destino="bronze"):
        base = cls.para_unidade_base(valor, origem)
        destino = str(destino or "bronze").lower()
        if destino not in cls.UNIDADES:
            raise ValueError(f"Unidade monetária inválida: {destino}")
        return base / cls.UNIDADES[destino]

    @classmethod
    def decompor(cls, valor_bronze):
        restante = cls._valor(valor_bronze).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        resultado = {}
        for unidade in cls.ORDEM:
            fator = cls.UNIDADES[unidade]
            quantidade = int(restante // fator)
            resultado[unidade] = quantidade
            restante -= quantidade * fator
        return resultado

    @classmethod
    def formatar(cls, valor_bronze):
        partes = cls.decompor(valor_bronze)
        nomes = {"bronze": "🟤 Bronze", "prata": "⚪ Prata", "ouro": "🟡 Ouro", "estelar": "✨ Estelar"}
        return " | ".join(f"{quantidade:,} {nomes[unidade]}" for unidade, quantidade in partes.items() if quantidade) or "0 🟤 Bronze"

    @classmethod
    def normalizar_saldo(cls, documento, campo="saldo"):
        # Compatibilidade com saldos antigos: números simples continuam representando Bronze.
        bruto = documento.get(campo, documento.get("capital", 0))
        if isinstance(bruto, dict):
            total = Decimal("0")
            for unidade, quantidade in bruto.items():
                if str(unidade).lower() in cls.UNIDADES:
                    total += cls.para_unidade_base(quantidade, unidade)
            return total
        return cls._valor(bruto)
