# database/python/magias.py
from pymongo import MongoClient
import json
import os

class DatabaseMagias:
    def __init__(self, db):
        self.db = db
        self.colecao = db["Magias"] if db else None

    def get_magias(self, user_id: str, guild_id: str):
        """Busca as magias de um jogador"""
        if not self.colecao:
            return []
        
        try:
            doc = self.colecao.find_one({
                "ID": user_id,
                "guild_id": guild_id
            })
            
            if doc:
                return doc.get("magias", [])
            return []
        except Exception as e:
            print(f"❌ Erro ao buscar magias: {e}")
            return []

    def get_tipos_magia(self, user_id: str, guild_id: str, magia_id: str):
        """Busca os tipos de uma magia específica do jogador"""
        if not self.colecao:
            return []
        
        try:
            doc = self.colecao.find_one({
                "ID": user_id,
                "guild_id": guild_id,
                "magias": magia_id
            })
            
            if doc:
                # Procura a magia na lista de magias do jogador
                magias_lista = doc.get("magias", [])
                for magia in magias_lista:
                    if isinstance(magia, dict) and magia.get("id") == magia_id:
                        return magia.get("tipos", [])
                return []
            return []
        except Exception as e:
            print(f"❌ Erro ao buscar tipos da magia: {e}")
            return []

    def add_magia(self, user_id: str, guild_id: str, magia_id: str, tipos: list = None):
        """Adiciona uma magia ao jogador com seus tipos"""
        if not self.colecao:
            return False
        
        try:
            # Se tipos foi passado, adiciona como objeto com tipos
            if tipos:
                magia_data = {
                    "id": magia_id,
                    "tipos": tipos
                }
                resultado = self.colecao.update_one(
                    {
                        "ID": user_id,
                        "guild_id": guild_id
                    },
                    {
                        "$addToSet": {"magias": magia_data},
                        "$setOnInsert": {"Situação": "ativo"}
                    },
                    upsert=True
                )
            else:
                # Adiciona apenas o ID (sem tipos específicos)
                resultado = self.colecao.update_one(
                    {
                        "ID": user_id,
                        "guild_id": guild_id
                    },
                    {
                        "$addToSet": {"magias": magia_id},
                        "$setOnInsert": {"Situação": "ativo"}
                    },
                    upsert=True
                )
            return resultado.modified_count > 0 or resultado.upserted_id is not None
        except Exception as e:
            print(f"❌ Erro ao adicionar magia: {e}")
            return False

    def remove_magia(self, user_id: str, guild_id: str, magia_id: str):
        """Remove uma magia do jogador"""
        if not self.colecao:
            return False
        
        try:
            # Remove tanto se for string pura quanto se for objeto
            resultado = self.colecao.update_one(
                {
                    "ID": user_id,
                    "guild_id": guild_id
                },
                {
                    "$pull": {"magias": magia_id}
                }
            )
            
            # Se não removeu, tenta remover como objeto
            if resultado.modified_count == 0:
                resultado = self.colecao.update_one(
                    {
                        "ID": user_id,
                        "guild_id": guild_id
                    },
                    {
                        "$pull": {"magias": {"id": magia_id}}
                    }
                )
            
            return resultado.modified_count > 0
        except Exception as e:
            print(f"❌ Erro ao remover magia: {e}")
            return False

    def add_multiplas_magias(self, user_id: str, guild_id: str, magias_list: list):
        """Adiciona múltiplas magias ao jogador
        magias_list: [{"id": "fogo_bola", "tipos": ["dano", "projetil"]}, ...]
        """
        if not self.colecao:
            return False
        
        try:
            # Prepara os dados para adicionar
            magias_para_adicionar = []
            for magia in magias_list:
                if isinstance(magia, dict):
                    magias_para_adicionar.append(magia)
                else:
                    magias_para_adicionar.append(magia)
            
            resultado = self.colecao.update_one(
                {
                    "ID": user_id,
                    "guild_id": guild_id
                },
                {
                    "$addToSet": {"magias": {"$each": magias_para_adicionar}},
                    "$setOnInsert": {"Situação": "ativo"}
                },
                upsert=True
            )
            return resultado.modified_count > 0 or resultado.upserted_id is not None
        except Exception as e:
            print(f"❌ Erro ao adicionar múltiplas magias: {e}")
            return False

    def get_magia_doc(self, user_id: str, guild_id: str):
        """Busca o documento completo do jogador na coleção Magias"""
        if not self.colecao:
            return None
        
        try:
            return self.colecao.find_one({
                "ID": user_id,
                "guild_id": guild_id
            })
        except Exception as e:
            print(f"❌ Erro ao buscar documento: {e}")
            return None

    def criar_documento(self, user_id: str, guild_id: str):
        """Cria um documento vazio para o jogador na coleção Magias"""
        if not self.colecao:
            return False
        
        try:
            resultado = self.colecao.update_one(
                {
                    "ID": user_id,
                    "guild_id": guild_id
                },
                {
                    "$setOnInsert": {
                        "magias": [],
                        "Situação": "ativo"
                    }
                },
                upsert=True
            )
            return resultado.upserted_id is not None
        except Exception as e:
            print(f"❌ Erro ao criar documento: {e}")
            return False

    def deletar_documento(self, user_id: str, guild_id: str):
        """Deleta o documento do jogador na coleção Magias"""
        if not self.colecao:
            return False
        
        try:
            resultado = self.colecao.delete_one({
                "ID": user_id,
                "guild_id": guild_id
            })
            return resultado.deleted_count > 0
        except Exception as e:
            print(f"❌ Erro ao deletar documento: {e}")
            return False

    def count_magias(self, user_id: str, guild_id: str):
        """Conta quantas magias o jogador possui"""
        magias = self.get_magias(user_id, guild_id)
        return len(magias)

    def tem_magia(self, user_id: str, guild_id: str, magia_id: str):
        """Verifica se o jogador possui uma magia específica"""
        magias = self.get_magias(user_id, guild_id)
        for magia in magias:
            if isinstance(magia, dict):
                if magia.get("id") == magia_id:
                    return True
            elif magia == magia_id:
                return True
        return False

    def get_tipos_disponiveis(self):
        """Retorna todos os tipos de magia disponíveis"""
        return [
            "dano", "cura", "defesa", "controle", "suporte",
            "projetil", "area", "linha", "corpo a corpo",
            "protecao", "prisao", "destruicao", "utilidade"
        ]

# Instância global
db_magias = None

def init_db_magias(db):
    """Inicializa a instância global do DatabaseMagias"""
    global db_magias
    db_magias = DatabaseMagias(db)
    return db_magias