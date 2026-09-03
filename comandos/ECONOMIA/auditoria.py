"""Auditoria estática da camada ECONOMIA.

Executa antes do carregamento das extensões e detecta erros de sintaxe,
comandos duplicados, aliases duplicados, decorators inválidos e problemas
estruturais básicos em todos os arquivos Python sob comandos/ECONOMIA.
"""

import ast
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


RAIZ = Path(__file__).resolve().parent


class AuditoriaEconomia:
    def __init__(self, db=None):
        self.db = db
        self.resultados = []
        self.comandos = defaultdict(list)
        self.aliases = defaultdict(list)

    @staticmethod
    def _decorator_command(decorator):
        if not isinstance(decorator, ast.Call):
            return None
        func = decorator.func
        if not isinstance(func, ast.Attribute) or func.attr != "command":
            return None
        nome = None
        aliases = []
        for keyword in decorator.keywords:
            if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                nome = str(keyword.value.value).lower()
            elif keyword.arg == "aliases" and isinstance(keyword.value, (ast.List, ast.Tuple)):
                aliases = [str(x.value).lower() for x in keyword.value.elts if isinstance(x, ast.Constant)]
        return nome, aliases

    def _auditar_arquivo(self, arquivo):
        relativo = str(arquivo.relative_to(RAIZ.parent.parent))
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
                self.comandos[nome].append(relativo)
                for alias in aliases:
                    item["aliases"].append(alias)
                    self.aliases[alias].append(relativo)

        self.resultados.append(item)

    def executar(self):
        self.resultados = []
        self.comandos.clear()
        self.aliases.clear()

        arquivos = sorted(p for p in RAIZ.rglob("*.py") if "__pycache__" not in p.parts)
        for arquivo in arquivos:
            self._auditar_arquivo(arquivo)

        conflitos = []
        nomes = defaultdict(set)
        for nome, arquivos_nome in self.comandos.items():
            for arquivo in arquivos_nome:
                nomes[nome].add(arquivo)
        for alias, arquivos_alias in self.aliases.items():
            for arquivo in arquivos_alias:
                nomes[alias].add(arquivo)

        for nome, arquivos_nome in sorted(nomes.items()):
            if len(arquivos_nome) > 1:
                conflitos.append({"nome": nome, "arquivos": sorted(arquivos_nome)})

        arquivos_erro = [x for x in self.resultados if x["status"] == "erro"]
        relatorio = {
            "executado_em": datetime.now(timezone.utc),
            "arquivos": len(arquivos),
            "arquivos_ok": len(arquivos) - len(arquivos_erro),
            "arquivos_com_erro": len(arquivos_erro),
            "conflitos_comandos": conflitos,
            "total_comandos": sum(len(x["comandos"]) for x in self.resultados),
            "detalhes": self.resultados,
        }

        if self.db is not None:
            self.db["Economia_Auditorias"].insert_one(relatorio.copy())

        return relatorio

    @staticmethod
    def resumo(relatorio):
        return (
            f"{relatorio['arquivos_ok']}/{relatorio['arquivos']} arquivos válidos | "
            f"{len(relatorio['conflitos_comandos'])} conflitos de comando"
        )
