import json
import os

DATA_DIR = "data"


def _path(nome_arquivo: str) -> str:
    return os.path.join(DATA_DIR, f"{nome_arquivo}.json")


def carregar(nome_arquivo: str, padrao=None):
    """Carrega um JSON de data/<nome_arquivo>.json. Cria com valor padrão se não existir."""
    os.makedirs(DATA_DIR, exist_ok=True)
    caminho = _path(nome_arquivo)
    if not os.path.exists(caminho):
        salvar(nome_arquivo, padrao if padrao is not None else {})
        return padrao if padrao is not None else {}
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar(nome_arquivo: str, dados):
    os.makedirs(DATA_DIR, exist_ok=True)
    caminho = _path(nome_arquivo)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)