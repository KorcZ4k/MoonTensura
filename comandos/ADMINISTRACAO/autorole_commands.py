# commands/autorole_commands.py
import discord
from discord.ext import commands
from .autorole_manager import AutoroleManager

# No arquivo autorole_commands.py

# comandos/ADMINISTRACAO/autorole.py
import discord
from discord.ext import commands
from .autorole_manager import AutoroleManager

class AutoroleCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.autorole_manager = AutoroleManager()

    @commands.group(name="autorole", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def autorole(self, ctx):
        """Comando principal para gerenciar autorole"""
        config = self.autorole_manager.get_guild_config(ctx.guild.id)
        
        embed = discord.Embed(
            title="⚙️ Sistema de Autorole - Moon Tensura",
            description="Gerencie os cargos automáticos do servidor",
            color=discord.Color.blue()
        )

        # Status do sistema
        status = "✅ Ativado" if config["enabled"] else "❌ Desativado"
        embed.add_field(
            name="📊 Status do Sistema",
            value=status,
            inline=False
        )

        # Status da DM
        dm_enabled = self.autorole_manager.is_dm_enabled(ctx.guild.id)
        dm_status = "✅ Ativada" if dm_enabled else "❌ Desativada"
        embed.add_field(
            name="📨 DM de Boas-Vindas",
            value=dm_status,
            inline=False
        )

        # LISTA DE CARGOS CONFIGURADOS
        roles_text = ""
        auto_assign_list = config.get("auto_assign", [])
        
        if config.get("roles", {}):
            for name, role_id in config.get("roles", {}).items():
                role = ctx.guild.get_role(int(role_id))
                role_name = role.mention if role else f"Cargo não encontrado ({role_id})"
                
                # Verifica se está na lista de auto assign
                is_auto = "🔄" if name in auto_assign_list else "⏸️"
                roles_text += f"{is_auto} **{name}**: {role_name}\n"
        else:
            roles_text = "Nenhum cargo configurado"

        embed.add_field(
            name="🎭 Cargos Configurados",
            value=roles_text,
            inline=False
        )

        # Lista de cargos com auto assign ativo
        if auto_assign_list:
            auto_roles_text = ""
            for name in auto_assign_list:
                role_id = config.get("roles", {}).get(name)
                if role_id:
                    role = ctx.guild.get_role(int(role_id))
                    auto_roles_text += f"• {role.mention if role else name}\n"
            
            embed.add_field(
                name="🔄 Auto Assign Ativo",
                value=auto_roles_text if auto_roles_text else "Nenhum",
                inline=False
            )

        # Comandos disponíveis
        embed.add_field(
            name="📋 Comandos",
            value=(
                "**Ativação:**\n"
                "`!autorole toggle` - Ativar/Desativar sistema\n"
                "`!autorole dm` - Ativar/Desativar DM\n\n"
                "**Cargos:**\n"
                "`!autorole add <nome> <@cargo>` - Adicionar cargo\n"
                "`!autorole remove <nome>` - Remover cargo\n"
                "`!autorole auto <nome>` - Auto atribuição\n\n"
                "**DM:**\n"
                "`!autorole dmconfig` - Configurar DM\n"
                "`!autorole dmtitle <título>` - Título da DM\n"
                "`!autorole dmdesc <descrição>` - Descrição da DM\n"
                "`!autorole dmfooter <footer>` - Footer da DM"
            ),
            inline=False
        )

        embed.set_footer(text="Moon Tensura • Korczak Technologies")
        await ctx.send(embed=embed)

    @autorole.command(name="toggle")
    @commands.has_permissions(administrator=True)
    async def autorole_toggle(self, ctx):
        """Ativa ou desativa o sistema de autorole"""
        status = self.autorole_manager.toggle_enabled(ctx.guild.id)

        embed = discord.Embed(
            title="🔄 Sistema de Autorole",
            description=f"Sistema {'ativado' if status else 'desativado'} com sucesso!",
            color=discord.Color.green() if status else discord.Color.red()
        )
        await ctx.send(embed=embed)

    @autorole.command(name="add")
    @commands.has_permissions(administrator=True)
    async def autorole_add(self, ctx, name: str, role: discord.Role):
        """Adiciona um cargo à configuração"""
        self.autorole_manager.add_role_config(ctx.guild.id, name.lower(), role.id)

        embed = discord.Embed(
            title="✅ Cargo Adicionado",
            description=f"Cargo **{role.mention}** adicionado como `{name}`",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @autorole.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def autorole_remove(self, ctx, name: str):
        """Remove um cargo da configuração"""
        config = self.autorole_manager.get_guild_config(ctx.guild.id)

        if name.lower() not in config.get("roles", {}):
            embed = discord.Embed(
                title="❌ Erro",
                description=f"Cargo `{name}` não encontrado na configuração",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        self.autorole_manager.remove_role_config(ctx.guild.id, name.lower())

        embed = discord.Embed(
            title="🗑️ Cargo Removido",
            description=f"Cargo `{name}` removido da configuração",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

    @autorole.command(name="auto")
    @commands.has_permissions(administrator=True)
    async def autorole_auto(self, ctx, name: str):
        """Ativa/desativa atribuição automática de um cargo"""
        config = self.autorole_manager.get_guild_config(ctx.guild.id)

        if name.lower() not in config.get("roles", {}):
            embed = discord.Embed(
                title="❌ Erro",
                description=f"Cargo `{name}` não encontrado na configuração",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        status = self.autorole_manager.toggle_auto_assign(ctx.guild.id, name.lower())

        embed = discord.Embed(
            title="🔄 Auto Assign",
            description=f"Atribuição automática para `{name}` {'ativada' if status else 'desativada'}",
            color=discord.Color.green() if status else discord.Color.orange()
        )
        await ctx.send(embed=embed)

    @autorole.command(name="dm")
    @commands.has_permissions(administrator=True)
    async def autorole_dm(self, ctx):
        """Ativa ou desativa a DM de boas-vindas"""
        status = self.autorole_manager.toggle_dm(ctx.guild.id)

        embed = discord.Embed(
            title="📨 DM de Boas-Vindas",
            description=f"DM {'ativada' if status else 'desativada'} com sucesso!",
            color=discord.Color.green() if status else discord.Color.red()
        )
        await ctx.send(embed=embed)

    @autorole.command(name="dmconfig")
    @commands.has_permissions(administrator=True)
    async def autorole_dmconfig(self, ctx):
        """Mostra a configuração atual da DM"""
        dm_config = self.autorole_manager.get_dm_config(ctx.guild.id)

        embed = discord.Embed(
            title="📨 Configuração da DM",
            color=discord.Color.blue()
        )

        status = "✅ Ativada" if dm_config.get("enabled", False) else "❌ Desativada"
        embed.add_field(name="Status", value=status, inline=False)
        embed.add_field(name="Título", value=dm_config.get("title", "Não configurado"), inline=False)

        desc = dm_config.get("description", "Não configurada")
        if len(desc) > 1000:
            desc = desc[:997] + "..."
        embed.add_field(name="Descrição", value=desc, inline=False)

        embed.add_field(name="Footer", value=dm_config.get("footer", "Não configurado"), inline=False)
        embed.set_image(url= 'https://media.discordapp.net/attachments/1543063886939299962/1543811582537105478/ChatGPT_Image_29_de_ago._de_2026_18_39_01.png?ex=6a96e2d3&is=6a959153&hm=400fd5cd195a8a13aa97386a0208a39b675b93e657b1b1afeeba08a4533cc335&=&format=webp&quality=lossless&width=1280&height=511')
        embed.set_footer(text="Use !autorole dmtitle/dmdesc/dmfooter para editar")
        await ctx.send(embed=embed)

    @autorole.command(name="dmtitle")
    @commands.has_permissions(administrator=True)
    async def autorole_dmtitle(self, ctx, *, title: str):
        """Define o título da DM de boas-vindas"""
        config = self.autorole_manager.get_guild_config(ctx.guild.id)
        dm_config = config.get("dm_config", {})
        dm_config["title"] = title
        config["dm_config"] = dm_config
        self.autorole_manager.set_guild_config(ctx.guild.id, config)

        embed = discord.Embed(
            title="✅ Título Atualizado",
            description=f"Novo título: **{title}**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @autorole.command(name="dmdesc")
    @commands.has_permissions(administrator=True)
    async def autorole_dmdesc(self, ctx, *, description: str):
        """Define a descrição da DM de boas-vindas"""
        config = self.autorole_manager.get_guild_config(ctx.guild.id)
        dm_config = config.get("dm_config", {})
        dm_config["description"] = description
        config["dm_config"] = dm_config
        self.autorole_manager.set_guild_config(ctx.guild.id, config)

        embed = discord.Embed(
            title="✅ Descrição Atualizada",
            description="Nova descrição configurada com sucesso!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @autorole.command(name="dmfooter")
    @commands.has_permissions(administrator=True)
    async def autorole_dmfooter(self, ctx, *, footer: str):
        """Define o footer da DM de boas-vindas"""
        config = self.autorole_manager.get_guild_config(ctx.guild.id)
        dm_config = config.get("dm_config", {})
        dm_config["footer"] = footer
        config["dm_config"] = dm_config
        self.autorole_manager.set_guild_config(ctx.guild.id, config)

        embed = discord.Embed(
            title="✅ Footer Atualizado",
            description=f"Novo footer: **{footer}**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @autorole.command(name="dmthumbnail")
    @commands.has_permissions(administrator=True)
    async def autorole_dmthumbnail(self, ctx, url: str = None):
        """Define ou remove a thumbnail da DM"""
        config = self.autorole_manager.get_guild_config(ctx.guild.id)
        dm_config = config.get("dm_config", {})

        if url is None:
            dm_config["thumbnail_url"] = None
            message = "Thumbnail removida com sucesso!"
        else:
            dm_config["thumbnail_url"] = url
            message = f"Thumbnail atualizada: {url}"

        config["dm_config"] = dm_config
        self.autorole_manager.set_guild_config(ctx.guild.id, config)

        embed = discord.Embed(
            title="✅ Thumbnail Atualizada",
            description=message,
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AutoroleCommands(bot))
