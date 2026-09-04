"""Auditoria estática global dos comandos do bot.

Executa antes do carregamento das extensões e detecta erros de sintaxe,
comandos duplicados, aliases duplicados e colisões entre comandos e aliases
nas áreas RPG, ECONOMIA e ADMINISTRACAO.
"""

import ast
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


PROJETO = Path(__file__).resolve().parents[2]
AREAS_PADRAO = ("comandos/RPG", "comandos/ECONOMIA", "comandos/ADMINISTRACAO")


class AuditoriaEconomia:
    """Nome mantido por compatibilidade; agora audita todos os comandos principais."""

    def __init__(self, db=None, areas=None):
        self.db = db
        self.areas = tuple(areas or AREAS_PADRAO)
        self.resultados = []
        self.registros = defaultdict(list)

    @staticmethod
    def _decorator_command(decorator):
        if not isinstance(decorator, ast.Call):
            return None
        func = decorator.func
        if not isinstance(func, ast.Attribute) or func.attr not in {"command", "hybrid_command"}:
            return None

        nome = None
        aliases = []
        for keyword in decorator.keywords:
            if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                nome = str(keyword.value.value).lower()
            elif keyword.arg == "aliases" and isinstance(keyword.value, (ast.List, ast.Tuple)):
                aliases = [str(x.value).lower() for x in keyword.value.elts if isinstance(x, ast.Constant)]
        return nome, aliases

    def _registrar(self, nome, arquivo, linha, tipo):
        self.registros[nome].append({"arquivo": arquivo, "linha": linha, "tipo": tipo})

    def _auditar_arquivo(self, arquivo):
        relativo = str(arquivo.relative_to(PROJETO))
        item = {"arquivo": relativo, "status": "ok", "erros": [], "comandos": [], "aliases": []}
        try:
            texto = arquivo.read_text(encoding="utf-8")
            arvore = ast.parse(texto, filename=str(arquivo))
        except SyntaxError as erro:
            item["status"] = "erro"
            item["erros"].append(f"Sintaxe linha {erro.lineno}: {erro.msg}")
            self.resultados.append(item)
            return
        except Exception as erro:
            item["status"] = "erro"
            item["erros"].append(f"Leitura: {erro}")
            self.resultados.append(item)
            return

        for no in ast.walk(arvore):
            if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in no.decorator_list:
                dados = self._decorator_command(decorator)
                if dados is None:
                    continue
                nome, aliases = dados
                nome = nome or no.name.lower()
                item["comandos"].append(nome)
                self._registrar(nome, relativo, no.lineno, "comando")
                for alias in aliases:
                    item["aliases"].append(alias)
                    self._registrar(alias, relativo, no.lineno, "alias")

        self.resultados.append(item)

    def executar(self):
        self.resultados = []
        self.registros.clear()

        arquivos = []
        for area in self.areas:
            raiz = PROJETO / area
            if raiz.exists():
                arquivos.extend(p for p in raiz.rglob("*.py") if "__pycache__" not in p.parts)

        arquivos = sorted(set(arquivos))
        for arquivo in arquivos:
            self._auditar_arquivo(arquivo)

        conflitos = []
        for nome, registros in sorted(self.registros.items()):
            if len(registros) > 1:
                conflitos.append({"nome": nome, "registros": registros})

        arquivos_erro = [x for x in self.resultados if x["status"] == "erro"]
        relatorio = {
            "executado_em": datetime.now(timezone.utc),
            "areas": list(self.areas),
            "arquivos": len(arquivos),
            "arquivos_ok": len(arquivos) - len(arquivos_erro),
            "arquivos_com_erro": len(arquivos_erro),
            "conflitos_comandos": conflitos,
            "total_comandos": sum(len(x["comandos"]) for x in self.resultados),
            "total_aliases": sum(len(x["aliases"]) for x in self.resultados),
            "detalhes": self.resultados,
        }

        if self.db is not None:
            self.db["Economia_Auditorias"].insert_one(relatorio.copy())

        return relatorio

    @staticmethod
    def resumo(relatorio):
        return (
            f"{relatorio['arquivos_ok']}/{relatorio['arquivos']} arquivos válidos | "
            f"{len(relatorio['conflitos_comandos'])} conflitos de comando/alias"
        )
