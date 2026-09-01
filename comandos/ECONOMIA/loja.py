import discord
from discord.ext import commands
from database.python.mongodb import db
from database.python.Hunos import db_hunos
import json
import random

class Loja(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.itens = self._carregar_itens()
        print(f"✅ {len(self.itens)} itens carregados na loja")

    def _carregar_itens(self):
        """Carrega os itens da loja do JSON"""
        try:
            with open('database/json/loja/itens.json', 'r', encoding='utf-8') as f:
                dados = json.load(f)
                return dados.get("itens", [])
        except Exception as e:
            print(f"❌ Erro ao carregar itens da loja: {e}")
            return []

    def _get_item(self, item_id: str):
        """Busca um item pelo ID"""
        for item in self.itens:
            if item["id"].lower() == item_id.lower():
                return item
        return None

    def _get_inventario_jogador(self, user_id: str, guild_id: str):
        """Busca o inventário do jogador"""
        if db is None:
            return None
        
        jogadores = db["Jogadores"]
        jogador = jogadores.find_one({
            "ID": user_id,
            "guild_id": guild_id
        })
        
        if jogador:
            return jogador.get("inventario", {})
        return {}

    def _atualizar_inventario(self, user_id: str, guild_id: str, item_id: str, quantidade: int = 1):
        """Atualiza o inventário do jogador"""
        if db is None:
            return False
        
        jogadores = db["Jogadores"]
        
        # Busca o item para ver se é stackável
        item = self._get_item(item_id)
        if not item:
            return False
        
        if item.get("stackavel", False):
            # Incrementa a quantidade
            resultado = jogadores.update_one(
                {
                    "ID": user_id,
                    "guild_id": guild_id
                },
                {
                    "$inc": {f"inventario.{item_id}": quantidade}
                }
            )
        else:
            # Define como 1 (não stackável)
            resultado = jogadores.update_one(
                {
                    "ID": user_id,
                    "guild_id": guild_id
                },
                {
                    "$set": {f"inventario.{item_id}": 1}
                }
            )
        
        return resultado.modified_count > 0

    def _remover_inventario(self, user_id: str, guild_id: str, item_id: str, quantidade: int = 1):
        """Remove item do inventário"""
        if db is None:
            return False
        
        jogadores = db["Jogadores"]
        
        item = self._get_item(item_id)
        if not item:
            return False
        
        if item.get("stackavel", False):
            # Decrementa a quantidade
            resultado = jogadores.update_one(
                {
                    "ID": user_id,
                    "guild_id": guild_id,
                    f"inventario.{item_id}": {"$gte": quantidade}
                },
                {
                    "$inc": {f"inventario.{item_id}": -quantidade}
                }
            )
            # Se chegou a 0, remove o campo
            if resultado.modified_count > 0:
                jogadores.update_one(
                    {
                        "ID": user_id,
                        "guild_id": guild_id,
                        f"inventario.{item_id}": 0
                    },
                    {
                        "$unset": {f"inventario.{item_id}": ""}
                    }
                )
        else:
            # Remove o item completamente
            resultado = jogadores.update_one(
                {
                    "ID": user_id,
                    "guild_id": guild_id,
                    f"inventario.{item_id}": {"$exists": True}
                },
                {
                    "$unset": {f"inventario.{item_id}": ""}
                }
            )
        
        return resultado.modified_count > 0

    def _aplicar_efeito_item(self, user_id: str, guild_id: str, item: dict):
        """Aplica o efeito de um item ao jogador"""
        jogadores = db["Jogadores"]
        
        tipo = item.get("tipo", "")
        item_id = item.get("id", "")
        
        if tipo == "consumivel":
            # Itens consumíveis (poções, etc)
            if item_id == "poção_vida":
                jogadores.update_one(
                    {"ID": user_id, "guild_id": guild_id},
                    {"$inc": {"Vida": 50}}  # 50% da vida
                )
            elif item_id == "poção_mana":
                jogadores.update_one(
                    {"ID": user_id, "guild_id": guild_id},
                    {"$inc": {"Mana": 50}}  # 50% da mana
                )
            elif item_id == "poção_cura_total":
                jogadores.update_one(
                    {"ID": user_id, "guild_id": guild_id},
                    {"$set": {"Vida": "Vida_Maxima", "Mana": "Mana Total"}}
                )
            elif item_id == "pocao_xp":
                jogadores.update_one(
                    {"ID": user_id, "guild_id": guild_id},
                    {"$inc": {"XP": 500}}
                )
            
            return True
            
        elif tipo == "permanente":
            # Itens permanentes (pedras de atributo, amuletos)
            if "pedra_forca" in item_id:
                jogadores.update_one(
                    {"ID": user_id, "guild_id": guild_id},
                    {"$inc": {"Força": 5}}
                )
            elif "pedra_defesa" in item_id:
                jogadores.update_one(
                    {"ID": user_id, "guild_id": guild_id},
                    {"$inc": {"Defesa": 5}}
                )
            elif "pedra_velocidade" in item_id:
                jogadores.update_one(
                    {"ID": user_id, "guild_id": guild_id},
                    {"$inc": {"Velocidade": 5}}
                )
            elif item_id == "amulet_roubo":
                jogadores.update_one(
                    {"ID": user_id, "guild_id": guild_id},
                    {"$set": {"amulet_sorte": True}}
                )
            elif item_id == "dado_carregado":
                jogadores.update_one(
                    {"ID": user_id, "guild_id": guild_id},
                    {"$set": {"dado_carregado": True}}
                )
            
            return True
            
        return False

    @commands.group(name="loja", aliases=["shop"], invoke_without_command=True)
    async def loja(self, ctx):
        """Comando principal da loja"""
        embed = discord.Embed(
            title="🏪 Loja Moon Tensura",
            description="Bem-vindo à loja oficial! Use Hunos para comprar itens.",
            color=discord.Color.gold()
        )
        
        # Mostra as categorias
        categorias = {}
        for item in self.itens:
            categoria = item.get("categoria", "outros")
            if categoria not in categorias:
                categorias[categoria] = 0
            categorias[categoria] += 1
        
        texto_categorias = ""
        for categoria, qtd in categorias.items():
            emoji = {
                "utilidade": "🔧",
                "cura": "💚",
                "atributo": "⚔️",
                "skin": "👕",
                "sorte": "🍀",
                "experiencia": "⭐"
            }.get(categoria, "📦")
            texto_categorias += f"{emoji} **{categoria.capitalize()}** - {qtd} itens\n"
        
        embed.add_field(
            name="📂 Categorias",
            value=texto_categorias,
            inline=False
        )
        
        # Saldo do jogador
        saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        embed.add_field(
            name="💰 Seu Saldo",
            value=f"{saldo:,} Hunos",
            inline=False
        )
        
        embed.add_field(
            name="📋 Comandos",
            value=(
                "`!loja listar` - Listar todos os itens\n"
                "`!loja comprar <id> [quantidade]` - Comprar item\n"
                "`!loja usar <id>` - Usar item do inventário\n"
                "`!loja inventario` - Ver seu inventário\n"
                "`!loja categoria <categoria>` - Ver itens por categoria"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

    @loja.command(name="listar", aliases=["lista", "itens"])
    async def loja_listar(self, ctx):
        """Lista todos os itens da loja"""
        embed = discord.Embed(
            title="📋 Todos os Itens da Loja",
            description="Use `!loja comprar <id>` para comprar",
            color=discord.Color.gold()
        )
        
        # Agrupa por categoria
        categorias = {}
        for item in self.itens:
            categoria = item.get("categoria", "outros")
            if categoria not in categorias:
                categorias[categoria] = []
            categorias[categoria].append(item)
        
        for categoria, itens in categorias.items():
            texto = ""
            for item in itens[:10]:  # Limita a 10 por categoria
                emoji_raridade = {
                    "comum": "⬜",
                    "raro": "🟦",
                    "epico": "🟪",
                    "lendario": "🟧"
                }.get(item.get("raridade", "comum"), "⬜")
                
                texto += f"{emoji_raridade} `{item['id']}` **{item['nome']}** - {item['preco']:,} Hunos\n"
                texto += f"  └ {item['descricao'][:50]}...\n"
            
            embed.add_field(
                name=f"📂 {categoria.capitalize()} ({len(itens)} itens)",
                value=texto if texto else "Nenhum item",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @loja.command(name="categoria")
    async def loja_categoria(self, ctx, categoria: str):
        """Mostra itens de uma categoria específica"""
        categoria = categoria.lower()
        
        itens_categoria = [item for item in self.itens if item.get("categoria", "").lower() == categoria]
        
        if not itens_categoria:
            await ctx.send(f"❌ Categoria `{categoria}` não encontrada.")
            return
        
        embed = discord.Embed(
            title=f"📂 Itens da Categoria: {categoria.capitalize()}",
            color=discord.Color.gold()
        )
        
        for item in itens_categoria[:15]:
            emoji_raridade = {
                "comum": "⬜",
                "raro": "🟦",
                "epico": "🟪",
                "lendario": "🟧"
            }.get(item.get("raridade", "comum"), "⬜")
            
            embed.add_field(
                name=f"{emoji_raridade} {item['nome']}",
                value=f"`{item['id']}`\n{item['descricao']}\n💰 {item['preco']:,} Hunos\n📦 {item.get('tipo', 'N/A')}",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @loja.command(name="comprar")
    async def loja_comprar(self, ctx, item_id: str, quantidade: int = 1):
        """Compra um item da loja
        Uso: !loja comprar <id> [quantidade]
        """
        # Busca o item
        item = self._get_item(item_id)
        if not item:
            await ctx.send(f"❌ Item `{item_id}` não encontrado na loja.")
            return
        
        # Verifica se a quantidade é válida
        if quantidade < 1:
            await ctx.send("❌ Quantidade deve ser maior que 0.")
            return
        
        # Verifica se é stackável
        if not item.get("stackavel", False) and quantidade > 1:
            await ctx.send(f"❌ `{item['nome']}` não é stackável. Compre apenas 1.")
            return
        
        # Verifica limite máximo
        maximo = item.get("maximo", 99)
        if quantidade > maximo:
            await ctx.send(f"❌ Você só pode comprar no máximo {maximo} de `{item['nome']}`.")
            return
        
        # Calcula o preço total
        preco_total = item["preco"] * quantidade
        
        # Verifica saldo do jogador
        saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        
        if saldo < preco_total:
            await ctx.send(f"❌ Saldo insuficiente! Você tem {saldo:,} Hunos, precisa de {preco_total:,} Hunos.")
            return
        
        # Verifica se já tem o item (se não for stackável)
        if not item.get("stackavel", False):
            inventario = self._get_inventario_jogador(str(ctx.author.id), str(ctx.guild.id))
            if inventario and item_id in inventario:
                await ctx.send(f"❌ Você já possui `{item['nome']}`. Itens não stackáveis só podem ter 1.")
                return
        
        # Remove os Hunos
        sucesso_remover = db_hunos.remove_hunos(str(ctx.author.id), str(ctx.guild.id), preco_total)
        
        if not sucesso_remover:
            await ctx.send("❌ Erro ao processar a compra. Tente novamente.")
            return
        
        # Adiciona ao inventário
        sucesso_adicionar = self._atualizar_inventario(str(ctx.author.id), str(ctx.guild.id), item_id, quantidade)
        
        if not sucesso_adicionar:
            # Reverte a remoção dos Hunos se falhar
            db_hunos.add_hunos(str(ctx.author.id), str(ctx.guild.id), preco_total)
            await ctx.send("❌ Erro ao adicionar ao inventário. Compra cancelada.")
            return
        
        embed = discord.Embed(
            title="✅ Compra Realizada!",
            description=f"Você comprou **{quantidade}x {item['nome']}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Preço Total", value=f"{preco_total:,} Hunos", inline=True)
        embed.add_field(name="Saldo Restante", value=f"{saldo - preco_total:,} Hunos", inline=True)
        embed.set_footer(text=f"ID: {item_id} | Categoria: {item.get('categoria', 'N/A')}")
        
        await ctx.send(embed=embed)

    @loja.command(name="inventario", aliases=["inv"])
    async def loja_inventario(self, ctx):
        """Mostra o inventário do jogador"""
        inventario = self._get_inventario_jogador(str(ctx.author.id), str(ctx.guild.id))
        
        if not inventario:
            await ctx.send("❌ Seu inventário está vazio.")
            return
        
        embed = discord.Embed(
            title=f"🎒 Inventário de {ctx.author.display_name}",
            color=discord.Color.blue()
        )
        
        # Agrupa por categoria
        itens_por_categoria = {}
        for item_id, quantidade in inventario.items():
            item = self._get_item(item_id)
            if item:
                categoria = item.get("categoria", "outros")
                if categoria not in itens_por_categoria:
                    itens_por_categoria[categoria] = []
                itens_por_categoria[categoria].append({
                    "item": item,
                    "quantidade": quantidade
                })
        
        if not itens_por_categoria:
            await ctx.send("❌ Seu inventário está vazio.")
            return
        
        for categoria, itens in itens_por_categoria.items():
            texto = ""
            for data in itens[:10]:
                item = data["item"]
                qtd = data["quantidade"]
                texto += f"• **{item['nome']}** x{qtd}\n"
            
            embed.add_field(
                name=f"📂 {categoria.capitalize()}",
                value=texto if texto else "Vazio",
                inline=False
            )
        
        total_itens = sum(data["quantidade"] for itens in itens_por_categoria.values() for data in itens)
        embed.set_footer(text=f"Total de itens: {total_itens}")
        
        await ctx.send(embed=embed)

    @loja.command(name="usar")
    async def loja_usar(self, ctx, item_id: str, quantidade: int = 1):
        """Usa um item do inventário
        Uso: !loja usar <id> [quantidade]
        """
        # Verifica se o item existe
        item = self._get_item(item_id)
        if not item:
            await ctx.send(f"❌ Item `{item_id}` não encontrado.")
            return
        
        # Verifica se o jogador tem o item
        inventario = self._get_inventario_jogador(str(ctx.author.id), str(ctx.guild.id))
        
        if not inventario or item_id not in inventario:
            await ctx.send(f"❌ Você não possui `{item['nome']}`.")
            return
        
        qtd_atual = inventario.get(item_id, 0)
        
        if qtd_atual < quantidade:
            await ctx.send(f"❌ Você só tem {qtd_atual}x de `{item['nome']}`, precisa de {quantidade}.")
            return
        
        # Verifica se o item é usável
        tipo = item.get("tipo", "")
        if tipo not in ["consumivel", "permanente"]:
            await ctx.send(f"❌ `{item['nome']}` não pode ser usado.")
            return
        
        # Aplica o efeito
        sucesso = self._aplicar_efeito_item(str(ctx.author.id), str(ctx.guild.id), item)
        
        if not sucesso:
            await ctx.send(f"❌ Erro ao usar `{item['nome']}`.")
            return
        
        # Remove do inventário
        self._remover_inventario(str(ctx.author.id), str(ctx.guild.id), item_id, quantidade)
        
        embed = discord.Embed(
            title="✅ Item Usado!",
            description=f"Você usou **{quantidade}x {item['nome']}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Efeito", value=item['descricao'], inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="additem")
    @commands.has_permissions(administrator=True)
    async def additem(self, ctx, membro: discord.Member, item_id: str, quantidade: int = 1):
        """Adiciona um item ao inventário de um jogador (Admin)
        Uso: !additem @membro item_id 5
        """
        item = self._get_item(item_id)
        if not item:
            await ctx.send(f"❌ Item `{item_id}` não encontrado.")
            return
        
        sucesso = self._atualizar_inventario(str(membro.id), str(ctx.guild.id), item_id, quantidade)
        
        if sucesso:
            await ctx.send(f"✅ {quantidade}x `{item['nome']}` adicionado a {membro.mention}")
        else:
            await ctx.send("❌ Erro ao adicionar item.")

async def setup(bot):
    await bot.add_cog(Loja(bot))