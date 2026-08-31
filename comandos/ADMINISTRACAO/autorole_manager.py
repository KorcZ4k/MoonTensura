# utils/autorole_manager.py
import json
import os
from typing import Optional, Dict, List, Any
import discord

class AutoroleManager:
    def __init__(self, file_path: str = "data/autorole_config.json"):
        self.file_path = file_path
        self.config = self._load_config()
        self._ensure_data_directory()
        
    def _ensure_data_directory(self):
        """Cria o diretório data se não existir"""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
    def _load_config(self) -> Dict[str, Any]:
        """Carrega a configuração do JSON"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Cria configuração padrão
            default_config = {
                "guilds": {},
                "default_config": {
                    "enabled": False,
                    "roles": {},
                    "auto_assign": [],
                    "dm_config": {
                        "enabled": False,
                        "title": "🌙 Bem-vindo ao Moon Tensura!",
                        "description": "Olá {user}! Seja bem-vindo ao servidor **Moon Tensura**!\n\n{roles_info}\n\nAproveite sua estadia! 🎉",
                        "footer": "Moon Tensura • Korczak Technologies",
                        "thumbnail_url": None
                    }
                }
            }
            self._save_config(default_config)
            return default_config
            
    def _save_config(self, config: Optional[Dict] = None):
        """Salva a configuração no JSON"""
        if config is None:
            config = self.config
            
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        """Obtém a configuração de um servidor"""
        guild_id_str = str(guild_id)
        
        if guild_id_str not in self.config["guilds"]:
            # Cria configuração padrão para o servidor
            self.config["guilds"][guild_id_str] = self.config["default_config"].copy()
            self._save_config()
            
        return self.config["guilds"][guild_id_str]
    
    def set_guild_config(self, guild_id: int, config: Dict[str, Any]):
        """Define a configuração de um servidor"""
        self.config["guilds"][str(guild_id)] = config
        self._save_config()
        
    def is_enabled(self, guild_id: int) -> bool:
        """Verifica se o autorole está habilitado no servidor"""
        config = self.get_guild_config(guild_id)
        return config.get("enabled", False)
    
    def get_roles(self, guild_id: int) -> Dict[str, int]:
        """Obtém os cargos configurados para o servidor"""
        config = self.get_guild_config(guild_id)
        return config.get("roles", {})
    
    def get_auto_assign_roles(self, guild_id: int) -> List[int]:
        """Obtém a lista de cargos para atribuição automática"""
        config = self.get_guild_config(guild_id)
        role_ids = []
        
        for role_name in config.get("auto_assign", []):
            role_id = config.get("roles", {}).get(role_name)
            if role_id:
                role_ids.append(int(role_id))
                
        return role_ids
    
    def get_dm_config(self, guild_id: int) -> Dict[str, Any]:
        """Obtém a configuração da DM de boas-vindas"""
        config = self.get_guild_config(guild_id)
        return config.get("dm_config", {})
    
    def is_dm_enabled(self, guild_id: int) -> bool:
        """Verifica se a DM está habilitada"""
        dm_config = self.get_dm_config(guild_id)
        return dm_config.get("enabled", False)
    
    def add_role_config(self, guild_id: int, role_name: str, role_id: int):
        """Adiciona um cargo à configuração"""
        config = self.get_guild_config(guild_id)
        config["roles"][role_name] = str(role_id)
        self.set_guild_config(guild_id, config)
        
    def remove_role_config(self, guild_id: int, role_name: str):
        """Remove um cargo da configuração"""
        config = self.get_guild_config(guild_id)
        if role_name in config["roles"]:
            del config["roles"][role_name]
            self.set_guild_config(guild_id, config)
            
    def toggle_auto_assign(self, guild_id: int, role_name: str) -> bool:
        """Ativa/desativa a atribuição automática de um cargo"""
        config = self.get_guild_config(guild_id)
        
        if role_name not in config["roles"]:
            return False
            
        if role_name in config["auto_assign"]:
            config["auto_assign"].remove(role_name)
        else:
            config["auto_assign"].append(role_name)
            
        self.set_guild_config(guild_id, config)
        return True
        
    def toggle_enabled(self, guild_id: int) -> bool:
        """Ativa/desativa o sistema de autorole"""
        config = self.get_guild_config(guild_id)
        config["enabled"] = not config["enabled"]
        self.set_guild_config(guild_id, config)
        return config["enabled"]
        
    def toggle_dm(self, guild_id: int) -> bool:
        """Ativa/desativa a DM de boas-vindas"""
        config = self.get_guild_config(guild_id)
        dm_config = config.get("dm_config", {})
        dm_config["enabled"] = not dm_config.get("enabled", False)
        config["dm_config"] = dm_config
        self.set_guild_config(guild_id, config)
        return dm_config["enabled"]
