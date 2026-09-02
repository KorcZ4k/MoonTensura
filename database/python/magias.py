import json
import os


class DatabaseMagias:

    def __init__(self, db):
        """
        Inicializa o sistema de banco de dados das magias.

        MongoDB:
            Magias
                ├── ID
                ├── guild_id
                ├── Situação
                ├── magias = FORMAS
                └── tipos = ELEMENTOS
        """

        self.db = db

        # Coleção MongoDB
        self.colecao = (
            db["Magias"]
            if db is not None
            else None
        )

        # Diretório base do projeto
        diretorio_atual = os.path.dirname(
            os.path.abspath(__file__)
        )

        # database/python/
        # sobe uma pasta para database/
        diretorio_database = os.path.dirname(
            diretorio_atual
        )

        # Arquivos JSON
        self.arquivo_formas = os.path.join(
            diretorio_database,
            "json",
            "magias",
            "formas.json"
        )

        self.arquivo_elementos = os.path.join(
            diretorio_database,
            "json",
            "magias",
            "elementos.json"
        )

    # ============================================================
    # FUNÇÕES JSON
    # ============================================================

    def _carregar_json(self, caminho):
        """
        Carrega um arquivo JSON.

        Retorna {} caso ocorra algum erro.
        """

        try:

            if not os.path.exists(caminho):

                print(
                    f"❌ Arquivo JSON não encontrado: "
                    f"{caminho}"
                )

                return {}

            with open(
                caminho,
                "r",
                encoding="utf-8"
            ) as arquivo:

                return json.load(arquivo)

        except json.JSONDecodeError as erro:

            print(
                f"❌ Erro ao ler JSON "
                f"{caminho}: {erro}"
            )

            return {}

        except Exception as erro:

            print(
                f"❌ Erro ao carregar "
                f"{caminho}: {erro}"
            )

            return {}

    def _normalizar(self, texto):
        """
        Normaliza texto para comparações.
        """

        if texto is None:
            return ""

        return str(texto).strip().lower()

    def _buscar_item(self, lista, identificador):
        """
        Busca um item por ID ou nome.
        """

        identificador = self._normalizar(
            identificador
        )

        for item in lista:

            if isinstance(item, dict):

                item_id = self._normalizar(
                    item.get("id")
                    or item.get("ID")
                    or ""
                )

                item_nome = self._normalizar(
                    item.get("nome")
                    or item.get("Nome")
                    or ""
                )

                if identificador == item_id:
                    return item

                if identificador == item_nome:
                    return item

            else:

                if (
                    self._normalizar(item)
                    == identificador
                ):
                    return item

        return None

    # ============================================================
    # FORMAS
    # ============================================================

    def get_formas_catalogo(self):
        """
        Retorna todas as formas existentes
        no arquivo formas.json.
        """

        dados = self._carregar_json(
            self.arquivo_formas
        )

        if isinstance(dados, dict):

            formas = dados.get(
                "formas",
                []
            )

            if isinstance(formas, list):
                return formas

        elif isinstance(dados, list):

            return dados

        return []

    def get_forma(self, forma_id):
        """
        Busca uma forma específica no catálogo.

        Exemplo:
            get_forma("bola")
        """

        formas = self.get_formas_catalogo()

        return self._buscar_item(
            formas,
            forma_id
        )

    def forma_existe(self, forma_id):
        """
        Verifica se uma forma existe
        no formas.json.
        """

        return (
            self.get_forma(forma_id)
            is not None
        )

    # ============================================================
    # ELEMENTOS
    # ============================================================

    def get_elementos_catalogo(self):
        """
        Retorna todos os elementos existentes
        no arquivo elementos.json.
        """

        dados = self._carregar_json(
            self.arquivo_elementos
        )

        if isinstance(dados, dict):

            elementos = dados.get(
                "elementos",
                []
            )

            if isinstance(elementos, list):
                return elementos

        elif isinstance(dados, list):

            return dados

        return []

    def get_elemento(self, elemento_id):
        """
        Busca um elemento específico
        no elementos.json.

        Exemplo:
            get_elemento("fogo")
        """

        elementos = self.get_elementos_catalogo()

        return self._buscar_item(
            elementos,
            elemento_id
        )

    def elemento_existe(self, elemento_id):
        """
        Verifica se um elemento existe
        no elementos.json.
        """

        return (
            self.get_elemento(elemento_id)
            is not None
        )

    # ============================================================
    # DOCUMENTO DO JOGADOR
    # ============================================================

    def get_magia_doc(
        self,
        user_id,
        guild_id
    ):
        """
        Busca o documento completo de magias do jogador.

        Estrutura:

        {
            "ID": "...",
            "guild_id": "...",
            "Situação": "ativo",

            "magias": [
                "bola",
                "raio"
            ],

            "tipos": [
                "fogo"
            ]
        }
        """

        if self.colecao is None:
            return None

        try:

            return self.colecao.find_one({
                "ID": str(user_id),
                "guild_id": str(guild_id)
            })

        except Exception as erro:

            print(
                f"❌ Erro ao buscar documento "
                f"de magias: {erro}"
            )

            return None

    def criar_documento(
        self,
        user_id,
        guild_id,
        situacao="ativo"
    ):
        """
        Cria um documento de magias vazio.

        magias = FORMAS
        tipos = ELEMENTOS
        """

        if self.colecao is None:
            return False

        try:

            resultado = self.colecao.update_one(

                {
                    "ID": str(user_id),
                    "guild_id": str(guild_id)
                },

                {
                    "$setOnInsert": {
                        "ID": str(user_id),
                        "guild_id": str(guild_id),
                        "Situação": situacao,
                        "magias": [],
                        "tipos": []
                    }
                },

                upsert=True
            )

            return (
                resultado.upserted_id is not None
                or resultado.matched_count > 0
            )

        except Exception as erro:

            print(
                f"❌ Erro ao criar documento "
                f"de magias: {erro}"
            )

            return False

    # ============================================================
    # FORMAS DO JOGADOR
    #
    # MONGODB:
    # magias = FORMAS
    # ============================================================

    def get_magias(
        self,
        user_id,
        guild_id
    ):
        """
        Retorna as FORMAS do jogador.

        Apesar do nome do campo ser 'magias',
        nesse sistema ele representa as formas.
        """

        documento = self.get_magia_doc(
            user_id,
            guild_id
        )

        if not documento:
            return []

        magias = documento.get(
            "magias",
            []
        )

        if not isinstance(magias, list):
            return []

        return magias

    def get_formas(
        self,
        user_id,
        guild_id
    ):
        """
        Alias de get_magias().

        magias no MongoDB = formas.
        """

        return self.get_magias(
            user_id,
            guild_id
        )

    def tem_magia(
        self,
        user_id,
        guild_id,
        forma_id
    ):
        """
        Verifica se o jogador possui uma forma.
        """

        formas = self.get_formas(
            user_id,
            guild_id
        )

        forma_id = self._normalizar(
            forma_id
        )

        for forma in formas:

            if isinstance(forma, dict):

                id_atual = (
                    forma.get("id")
                    or forma.get("ID")
                    or forma.get("nome")
                    or ""
                )

            else:

                id_atual = forma

            if (
                self._normalizar(id_atual)
                == forma_id
            ):
                return True

        return False

    def tem_forma(
        self,
        user_id,
        guild_id,
        forma_id
    ):
        """
        Alias de tem_magia().
        """

        return self.tem_magia(
            user_id,
            guild_id,
            forma_id
        )

    def add_magia(
        self,
        user_id,
        guild_id,
        forma_id
    ):
        """
        Adiciona uma FORMA ao jogador.

        Campo MongoDB:
            magias
        """

        if self.colecao is None:
            return False

        try:

            resultado = self.colecao.update_one(

                {
                    "ID": str(user_id),
                    "guild_id": str(guild_id)
                },

                {
                    "$addToSet": {
                        "magias": str(forma_id)
                    },

                    "$setOnInsert": {
                        "ID": str(user_id),
                        "guild_id": str(guild_id),
                        "Situação": "ativo",
                        "tipos": []
                    }
                },

                upsert=True
            )

            return (
                resultado.modified_count > 0
                or resultado.upserted_id is not None
            )

        except Exception as erro:

            print(
                f"❌ Erro ao adicionar forma: "
                f"{erro}"
            )

            return False

    def add_forma(
        self,
        user_id,
        guild_id,
        forma_id
    ):
        """
        Alias de add_magia().
        """

        return self.add_magia(
            user_id,
            guild_id,
            forma_id
        )

    def add_multiplas_magias(
        self,
        user_id,
        guild_id,
        formas
    ):
        """
        Adiciona múltiplas FORMAS ao jogador.
        """

        if self.colecao is None:
            return False

        if not formas:
            return False

        try:

            formas_normalizadas = []

            for forma in formas:

                if isinstance(forma, dict):

                    forma_id = (
                        forma.get("id")
                        or forma.get("ID")
                        or forma.get("nome")
                    )

                    if forma_id:
                        formas_normalizadas.append(
                            str(forma_id)
                        )

                else:

                    formas_normalizadas.append(
                        str(forma)
                    )

            if not formas_normalizadas:
                return False

            resultado = self.colecao.update_one(

                {
                    "ID": str(user_id),
                    "guild_id": str(guild_id)
                },

                {
                    "$addToSet": {
                        "magias": {
                            "$each": formas_normalizadas
                        }
                    },

                    "$setOnInsert": {
                        "ID": str(user_id),
                        "guild_id": str(guild_id),
                        "Situação": "ativo",
                        "tipos": []
                    }
                },

                upsert=True
            )

            return (
                resultado.modified_count > 0
                or resultado.upserted_id is not None
            )

        except Exception as erro:

            print(
                f"❌ Erro ao adicionar formas: "
                f"{erro}"
            )

            return False

    def remove_magia(
        self,
        user_id,
        guild_id,
        forma_id
    ):
        """
        Remove uma forma do jogador.
        """

        if self.colecao is None:
            return False

        try:

            resultado = self.colecao.update_one(

                {
                    "ID": str(user_id),
                    "guild_id": str(guild_id)
                },

                {
                    "$pull": {
                        "magias": str(forma_id)
                    }
                }
            )

            return resultado.modified_count > 0

        except Exception as erro:

            print(
                f"❌ Erro ao remover forma: "
                f"{erro}"
            )

            return False

    def remove_forma(
        self,
        user_id,
        guild_id,
        forma_id
    ):
        """
        Alias de remove_magia().
        """

        return self.remove_magia(
            user_id,
            guild_id,
            forma_id
        )

    # ============================================================
    # ELEMENTOS DO JOGADOR
    #
    # MONGODB:
    # tipos = ELEMENTOS
    # ============================================================

    def get_tipos(
        self,
        user_id,
        guild_id
    ):
        """
        Retorna os ELEMENTOS do jogador.
        """

        documento = self.get_magia_doc(
            user_id,
            guild_id
        )

        if not documento:
            return []

        tipos = documento.get(
            "tipos",
            []
        )

        if not isinstance(tipos, list):
            return []

        return tipos

    def get_elementos(
        self,
        user_id,
        guild_id
    ):
        """
        Alias de get_tipos().

        tipos no MongoDB = elementos.
        """

        return self.get_tipos(
            user_id,
            guild_id
        )

    def tem_tipo(
        self,
        user_id,
        guild_id,
        elemento_id
    ):
        """
        Verifica se o jogador possui um elemento.
        """

        elementos = self.get_elementos(
            user_id,
            guild_id
        )

        elemento_id = self._normalizar(
            elemento_id
        )

        for elemento in elementos:

            if isinstance(elemento, dict):

                id_atual = (
                    elemento.get("id")
                    or elemento.get("ID")
                    or elemento.get("nome")
                    or ""
                )

            else:

                id_atual = elemento

            if (
                self._normalizar(id_atual)
                == elemento_id
            ):
                return True

        return False

    def tem_elemento(
        self,
        user_id,
        guild_id,
        elemento_id
    ):
        """
        Alias de tem_tipo().
        """

        return self.tem_tipo(
            user_id,
            guild_id,
            elemento_id
        )

    def add_tipo(
        self,
        user_id,
        guild_id,
        elemento_id
    ):
        """
        Adiciona um ELEMENTO ao jogador.

        Campo MongoDB:
            tipos
        """

        if self.colecao is None:
            return False

        try:

            resultado = self.colecao.update_one(

                {
                    "ID": str(user_id),
                    "guild_id": str(guild_id)
                },

                {
                    "$addToSet": {
                        "tipos": str(elemento_id)
                    },

                    "$setOnInsert": {
                        "ID": str(user_id),
                        "guild_id": str(guild_id),
                        "Situação": "ativo",
                        "magias": []
                    }
                },

                upsert=True
            )

            return (
                resultado.modified_count > 0
                or resultado.upserted_id is not None
            )

        except Exception as erro:

            print(
                f"❌ Erro ao adicionar elemento: "
                f"{erro}"
            )

            return False

    def add_elemento(
        self,
        user_id,
        guild_id,
        elemento_id
    ):
        """
        Alias de add_tipo().
        """

        return self.add_tipo(
            user_id,
            guild_id,
            elemento_id
        )

    def add_multiplos_tipos(
        self,
        user_id,
        guild_id,
        elementos
    ):
        """
        Adiciona múltiplos elementos ao jogador.
        """

        if self.colecao is None:
            return False

        if not elementos:
            return False

        try:

            elementos_normalizados = []

            for elemento in elementos:

                if isinstance(elemento, dict):

                    elemento_id = (
                        elemento.get("id")
                        or elemento.get("ID")
                        or elemento.get("nome")
                    )

                    if elemento_id:

                        elementos_normalizados.append(
                            str(elemento_id)
                        )

                else:

                    elementos_normalizados.append(
                        str(elemento)
                    )

            if not elementos_normalizados:
                return False

            resultado = self.colecao.update_one(

                {
                    "ID": str(user_id),
                    "guild_id": str(guild_id)
                },

                {
                    "$addToSet": {
                        "tipos": {
                            "$each": elementos_normalizados
                        }
                    },

                    "$setOnInsert": {
                        "ID": str(user_id),
                        "guild_id": str(guild_id),
                        "Situação": "ativo",
                        "magias": []
                    }
                },

                upsert=True
            )

            return (
                resultado.modified_count > 0
                or resultado.upserted_id is not None
            )

        except Exception as erro:

            print(
                f"❌ Erro ao adicionar elementos: "
                f"{erro}"
            )

            return False

    def remove_tipo(
        self,
        user_id,
        guild_id,
        elemento_id
    ):
        """
        Remove um elemento do jogador.
        """

        if self.colecao is None:
            return False

        try:

            resultado = self.colecao.update_one(

                {
                    "ID": str(user_id),
                    "guild_id": str(guild_id)
                },

                {
                    "$pull": {
                        "tipos": str(elemento_id)
                    }
                }
            )

            return resultado.modified_count > 0

        except Exception as erro:

            print(
                f"❌ Erro ao remover elemento: "
                f"{erro}"
            )

            return False

    def remove_elemento(
        self,
        user_id,
        guild_id,
        elemento_id
    ):
        """
        Alias de remove_tipo().
        """

        return self.remove_tipo(
            user_id,
            guild_id,
            elemento_id
        )

    # ============================================================
    # CONTADORES
    # ============================================================

    def count_magias(
        self,
        user_id,
        guild_id
    ):
        """
        Conta quantas formas o jogador possui.
        """

        return len(
            self.get_formas(
                user_id,
                guild_id
            )
        )

    def count_formas(
        self,
        user_id,
        guild_id
    ):
        """
        Alias de count_magias().
        """

        return self.count_magias(
            user_id,
            guild_id
        )

    def count_tipos(
        self,
        user_id,
        guild_id
    ):
        """
        Conta quantos elementos o jogador possui.
        """

        return len(
            self.get_elementos(
                user_id,
                guild_id
            )
        )

    def count_elementos(
        self,
        user_id,
        guild_id
    ):
        """
        Alias de count_tipos().
        """

        return self.count_tipos(
            user_id,
            guild_id
        )

    # ============================================================
    # DELETAR DOCUMENTO
    # ============================================================

    def deletar_documento(
        self,
        user_id,
        guild_id
    ):
        """
        Deleta o documento completo de magias
        do jogador.
        """

        if self.colecao is None:
            return False

        try:

            resultado = self.colecao.delete_one({

                "ID": str(user_id),
                "guild_id": str(guild_id)

            })

            return resultado.deleted_count > 0

        except Exception as erro:

            print(
                f"❌ Erro ao deletar documento "
                f"de magias: {erro}"
            )

            return False


# ================================================================
# INSTÂNCIA GLOBAL
# ================================================================

db_magias = None


def init_db_magias(db):
    """
    Inicializa a instância global do
    DatabaseMagias.
    """

    global db_magias

    db_magias = DatabaseMagias(db)

    return db_magias