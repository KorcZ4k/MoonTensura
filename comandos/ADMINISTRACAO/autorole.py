# events/autorole_events.py
import discord
from discord.ext import commands
from .autorole_manager import AutoroleManager

class AutoroleEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.autorole_manager = AutoroleManager()
        
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Evento executado quando um membro entra no servidor"""
        
        # Verifica se o autorole está habilitado
        if not self.autorole_manager.is_enabled(member.guild.id):
            return
            
        # 1. ATRIBUIÇÃO DE CARGOS
        role_ids = self.autorole_manager.get_auto_assign_roles(member.guild.id)
        roles_to_add = []
        role_names = []
        
        for role_id in role_ids:
            role = member.guild.get_role(role_id)
            if role:
                roles_to_add.append(role)
                role_names.append(role.mention)
                
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="Autorole - Moon Tensura")
                print(f"✅ Cargos atribuídos a {member}: {', '.join(role_names)}")
            except discord.Forbidden:
                print(f"❌ Sem permissão para adicionar cargos a {member}")
            except Exception as e:
                print(f"❌ Erro ao adicionar cargos: {e}")
                
        # 2. ENVIO DE DM PERSONALIZADA
        if self.autorole_manager.is_dm_enabled(member.guild.id):
            await self.send_welcome_dm(member)
            
    async def send_welcome_dm(self, member: discord.Member):
        """Envia DM personalizada para o novo membro"""
        try:
            dm_config = self.autorole_manager.get_dm_config(member.guild.id)
            
            # Obtém informações dos cargos
            config = self.autorole_manager.get_guild_config(member.guild.id)
            roles_info = ""
            
            for role_name, role_id in config.get("roles", {}).items():
                role = member.guild.get_role(int(role_id))
                if role:
                    roles_info += f"• {role.mention} - Cargo: {role_name.capitalize()}\n"
                    
            if not roles_info:
                roles_info = "• Nenhum cargo especial configurado"
            
            # Prepara o embed
            embed = discord.Embed(
                title=dm_config.get("title", "🌙 Bem-vindo ao Moon Tensura!"),
                description=dm_config.get("description", "").format(
                    user=member.display_name,
                    guild=member.guild.name,
                    roles_info=roles_info,
                    member_count=member.guild.member_count
                ),
                color=discord.Color.blue()
            )
            
            # Adiciona thumbnail se configurado
            thumbnail_url = dm_config.get("thumbnail_url")
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
                
            # Adiciona footer
            footer = dm_config.get("footer", "Moon Tensura • Korczak Technologies")
            embed.set_footer(text=footer)
            
            # Envia a DM
            await member.send(embed=embed)
            print(f"📨 DM enviada para {member}")
            
        except discord.Forbidden:
            print(f"❌ Não foi possível enviar DM para {member} (DM bloqueada)")
        except Exception as e:
            print(f"❌ Erro ao enviar DM: {e}")
            
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Evento executado quando um membro sai do servidor"""
        print(f"👋 {member} saiu do servidor {member.guild}")
        
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Evento executado quando um membro é atualizado"""
        # Verifica se o membro se tornou um booster
        if not before.premium_since and after.premium_since:
            config = self.autorole_manager.get_guild_config(after.guild.id)
            
            # Verifica se existe cargo configurado para booster
            booster_role_id = config.get("roles", {}).get("booster")
            if booster_role_id:
                role = after.guild.get_role(int(booster_role_id))
                if role and role not in after.roles:
                    try:
                        await after.add_roles(role, reason="Booster do servidor")
                        print(f"🚀 Cargo de booster adicionado a {after}")
                    except Exception as e:
                        print(f"❌ Erro ao adicionar cargo de booster: {e}")

async def setup(bot):
    await bot.add_cog(AutoroleEvents(bot))