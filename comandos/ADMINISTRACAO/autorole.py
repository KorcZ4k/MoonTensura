import discord
from discord.ext import commands
import json_db


class RoleButton(discord.ui.Button):
    def __init__(self, role_id: int, emoji: str, label: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label,
            emoji=emoji or None,
            custom_id=f"rolemenu:{role_id}"
        )
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        if role is None:
            await interaction.response.send_message("Esse cargo não existe mais.", ephemeral=True)
            return

        membro = interaction.user
        if role in membro.roles:
            await membro.remove_roles(role, reason="Rolemenu")
            await interaction.response.send_message(f"Cargo **{role.name}** removido.", ephemeral=True)
        else:
            await membro.add_roles(role, reason="Rolemenu")
            await interaction.response.send_message(f"Cargo **{role.name}** adicionado!", ephemeral=True)


class RoleMenuView(discord.ui.View):
    def __init__(self, roles_data: list):
        super().__init__(timeout=None)
        for r in roles_data:
            self.add_item(RoleButton(r["role_id"], r.get("emoji"), r["label"]))


class Autoroles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        rolemenus = json_db.carregar("rolemenus", {})
        for message_id, menu in rolemenus.items():
            if menu["roles"]:
                view = RoleMenuView(menu["roles"])
                self.bot.add_view(view, message_id=int(message_id))

    # ---------------- AUTOROLE DE ENTRADA ----------------

    @commands.group(name="autorole", invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def autorole(self, ctx):
        await ctx.send("Use `!autorole set @cargo`, `!autorole remove @cargo` ou `!autorole list`.")

    @autorole.command(name="set")
    @commands.has_permissions(manage_roles=True)
    async def autorole_set(self, ctx, cargo: discord.Role):
        config = json_db.carregar("config", {})
        gid = str(ctx.guild.id)
        config.setdefault(gid, {}).setdefault("welcome_roles", [])
        if cargo.id not in config[gid]["welcome_roles"]:
            config[gid]["welcome_roles"].append(cargo.id)
        json_db.salvar("config", config)
        await ctx.send(f"Cargo **{cargo.name}** será dado automaticamente a novos membros.")

    @autorole.command(name="remove")
    @commands.has_permissions(manage_roles=True)
    async def autorole_remove(self, ctx, cargo: discord.Role):
        config = json_db.carregar("config", {})
        gid = str(ctx.guild.id)
        if gid in config and cargo.id in config[gid].get("welcome_roles", []):
            config[gid]["welcome_roles"].remove(cargo.id)
            json_db.salvar("config", config)
        await ctx.send(f"Cargo **{cargo.name}** removido dos autoroles.")

    @autorole.command(name="list")
    @commands.has_permissions(manage_roles=True)
    async def autorole_list(self, ctx):
        config = json_db.carregar("config", {})
        gid = str(ctx.guild.id)
        ids = config.get(gid, {}).get("welcome_roles", [])
        cargos = [ctx.guild.get_role(rid) for rid in ids]
        cargos = [c for c in cargos if c]
        if not cargos:
            await ctx.send("Nenhum autorole configurado.")
            return
        texto = "\n".join(f"- {c.mention}" for c in cargos)
        embed = discord.Embed(title="Autoroles de entrada", description=texto, color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = json_db.carregar("config", {})
        gid = str(member.guild.id)
        ids = config.get(gid, {}).get("welcome_roles", [])
        cargos = [member.guild.get_role(rid) for rid in ids]
        cargos = [c for c in cargos if c]
        if cargos:
            await member.add_roles(*cargos, reason="Autorole de entrada")

    # ---------------- MENU DE CARGOS (BOTÕES) ----------------

    @commands.group(name="rolemenu", invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def rolemenu(self, ctx):
        await ctx.send("Use `!rolemenu create <titulo> | <descrição>` para criar um menu.")

    @rolemenu.command(name="create")
    @commands.has_permissions(manage_roles=True)
    async def rolemenu_create(self, ctx, *, texto: str):
        titulo, _, descricao = texto.partition("|")
        embed = discord.Embed(
            title=titulo.strip(),
            description=descricao.strip() or "Clique nos botões abaixo para pegar ou remover um cargo.",
            color=discord.Color.blurple()
        )
        msg = await ctx.send(embed=embed)

        rolemenus = json_db.carregar("rolemenus", {})
        rolemenus[str(msg.id)] = {
            "guild_id": ctx.guild.id,
            "channel_id": ctx.channel.id,
            "roles": []
        }
        json_db.salvar("rolemenus", rolemenus)
        await ctx.send(f"Menu criado! Use `!rolemenu addrole {msg.id} @cargo emoji nome do botão`.")

    @rolemenu.command(name="addrole")
    @commands.has_permissions(manage_roles=True)
    async def rolemenu_addrole(self, ctx, message_id: int, cargo: discord.Role, emoji: str, *, label: str):
        rolemenus = json_db.carregar("rolemenus", {})
        menu = rolemenus.get(str(message_id))
        if not menu:
            await ctx.send("Menu não encontrado (confira o ID da mensagem).")
            return
        if len(menu["roles"]) >= 25:
            await ctx.send("Esse menu já atingiu o limite de 25 botões do Discord.")
            return

        menu["roles"].append({"role_id": cargo.id, "emoji": emoji, "label": label})
        json_db.salvar("rolemenus", rolemenus)

        canal = ctx.guild.get_channel(menu["channel_id"])
        mensagem = await canal.fetch_message(message_id)
        view = RoleMenuView(menu["roles"])
        await mensagem.edit(view=view)
        self.bot.add_view(view, message_id=message_id)

        await ctx.send(f"Cargo **{cargo.name}** adicionado ao menu.")

    @rolemenu.command(name="removerole")
    @commands.has_permissions(manage_roles=True)
    async def rolemenu_removerole(self, ctx, message_id: int, cargo: discord.Role):
        rolemenus = json_db.carregar("rolemenus", {})
        menu = rolemenus.get(str(message_id))
        if not menu:
            await ctx.send("Menu não encontrado.")
            return

        menu["roles"] = [r for r in menu["roles"] if r["role_id"] != cargo.id]
        json_db.salvar("rolemenus", rolemenus)

        canal = ctx.guild.get_channel(menu["channel_id"])
        mensagem = await canal.fetch_message(message_id)
        view = RoleMenuView(menu["roles"])
        await mensagem.edit(view=view)
        self.bot.add_view(view, message_id=message_id)

        await ctx.send(f"Cargo **{cargo.name}** removido do menu.")


async def setup(bot):
    await bot.add_cog(Autoroles(bot))