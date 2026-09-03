import discord
from discord.ext import commands
from database.python.mongodb import db
from database.python.Hunos import db_hunos
from comandos.ECONOMIA.GLOBAL.motor import MotorEconomiaGlobal
from comandos.ECONOMIA.GLOBAL.mercado import MercadoEconomico
import json

class Loja(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.itens = self._carregar_itens()
        self.motor = MotorEconomiaGlobal(db)
        self.mercado_economico = MercadoEconomico(self.motor)
        print(f"✅ {len(self.itens)} itens carregados na loja")

    def _carregar_itens(self):
        try:
            with open('database/json/loja/itens.json', 'r', encoding='utf-8') as f:
                return json.load(f).get('itens', [])
        except Exception as e:
            print(f'❌ Erro ao carregar itens da loja: {e}')
            return []

    def _get_item(self, item_id):
        return next((i for i in self.itens if i['id'].lower() == item_id.lower()), None)

    def _produto(self, item):
        produto = self.mercado_economico.normalizar_produto(item)
        self.mercado_economico.registrar_produto(**produto)
        return produto

    def _inventario(self, user_id, guild_id):
        jogador = db['Jogadores'].find_one({'ID': user_id, 'guild_id': guild_id})
        return jogador.get('inventario', {}) if jogador else {}

    def _adicionar_inventario(self, user_id, guild_id, item_id, quantidade):
        item = self._get_item(item_id)
        if not item: return False
        update = {'$inc': {f'inventario.{item_id}': quantidade}} if item.get('stackavel', False) else {'$set': {f'inventario.{item_id}': 1}}
        return db['Jogadores'].update_one({'ID': user_id, 'guild_id': guild_id}, update).modified_count > 0

    def _remover_inventario(self, user_id, guild_id, item_id, quantidade=1):
        item = self._get_item(item_id)
        if not item: return False
        query = {'ID': user_id, 'guild_id': guild_id}
        if item.get('stackavel', False):
            resultado = db['Jogadores'].update_one({**query, f'inventario.{item_id}': {'$gte': quantidade}}, {'$inc': {f'inventario.{item_id}': -quantidade}})
            if resultado.modified_count:
                db['Jogadores'].update_one({**query, f'inventario.{item_id}': 0}, {'$unset': {f'inventario.{item_id}': ''}})
            return resultado.modified_count > 0
        return db['Jogadores'].update_one({**query, f'inventario.{item_id}': {'$exists': True}}, {'$unset': {f'inventario.{item_id}': ''}}).modified_count > 0

    def _aplicar_efeito(self, user_id, guild_id, item):
        jogadores = db['Jogadores']; item_id = item['id']; tipo = item.get('tipo', '')
        if tipo == 'consumivel':
            if item_id == 'poção_vida':
                jogadores.update_one({'ID': user_id, 'guild_id': guild_id}, {'$inc': {'Vida': 50}})
            elif item_id == 'poção_mana':
                jogadores.update_one({'ID': user_id, 'guild_id': guild_id}, {'$inc': {'Mana': 50}})
            elif item_id == 'poção_cura_total':
                jogador = jogadores.find_one({'ID': user_id, 'guild_id': guild_id}) or {}
                vida_max = jogador.get('Vida_Maxima', jogador.get('Vida', 100))
                mana_max = jogador.get('Mana_Maxima', jogador.get('Mana_Max', jogador.get('Mana', 100)))
                jogadores.update_one({'ID': user_id, 'guild_id': guild_id}, {'$set': {'Vida': vida_max, 'Mana': mana_max}})
            elif item_id == 'pocao_xp':
                jogadores.update_one({'ID': user_id, 'guild_id': guild_id}, {'$inc': {'XP': 500}})
            elif item_id == 'pocao_xp_dobro':
                jogadores.update_one({'ID': user_id, 'guild_id': guild_id}, {'$set': {'xp_dobro_ate': __import__('datetime').datetime.utcnow().timestamp() + 1800}})
            else:
                return False
            return True
        if tipo == 'permanente':
            efeitos = {'pedra_forca': {'Força': 5}, 'pedra_defesa': {'Defesa': 5}, 'pedra_velocidade': {'Velocidade': 5}}
            if item_id in efeitos:
                jogadores.update_one({'ID': user_id, 'guild_id': guild_id}, {'$inc': efeitos[item_id]})
            elif item_id == 'amulet_roubo':
                jogadores.update_one({'ID': user_id, 'guild_id': guild_id}, {'$set': {'amulet_sorte': True}})
            elif item_id == 'dado_carregado':
                jogadores.update_one({'ID': user_id, 'guild_id': guild_id}, {'$set': {'dado_carregado': True}})
            else:
                return False
            return True
        return False

    async def _mercado(self, ctx):
        mercado = self.motor.mercado_do_canal(ctx.guild.id, ctx.channel.id)
        if mercado is None:
            await ctx.send(embed=discord.Embed(title='🏪 Mercado não configurado', description='Este canal não está configurado como estabelecimento econômico. Um administrador deve usar `!configurar_mercado` neste canal.', color=discord.Color.red()))
        return mercado

    @commands.group(name='loja', aliases=['shop'], invoke_without_command=True)
    @commands.guild_only()
    async def loja(self, ctx):
        mercado = await self._mercado(ctx)
        if not mercado: return
        embed = discord.Embed(title=f"🏪 {mercado['tipo'].capitalize()} {mercado.get('categoria', 'comum').capitalize()}", description='Preços dinâmicos conforme oferta, demanda, estoque e inflação.', color=discord.Color.gold())
        embed.add_field(name='💰 Seu saldo', value=f"{db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id)):,} Hunos")
        embed.add_field(name='📈 Multiplicador', value=f"{mercado.get('multiplicador_preco', 1.0):.3f}x")
        embed.add_field(name='📋 Comandos', value='`!loja listar`\n`!loja comprar <id> [quantidade]`\n`!loja usar <id>`\n`!loja categoria <categoria>`\n`!loja inventario`', inline=False)
        await ctx.send(embed=embed)

    @loja.command(name='listar', aliases=['lista', 'itens'])
    async def listar(self, ctx):
        mercado = await self._mercado(ctx)
        if not mercado: return
        embed = discord.Embed(title='📋 Produtos disponíveis', color=discord.Color.gold())
        encontrados = 0
        for item in self.itens:
            produto = self._produto(item)
            if not self.mercado_economico.categoria_permitida(mercado, produto['categoria']): continue
            cotacao = self.mercado_economico.cotar(ctx.guild.id, ctx.channel.id, produto)
            if 'erro' in cotacao: continue
            embed.add_field(name=f"{item['nome']} — `{item['id']}`", value=f"💰 {cotacao['preco_unitario']:,} Hunos\n📦 Estoque: {cotacao['estoque']}", inline=False)
            encontrados += 1
            if encontrados >= 20: break
        if not encontrados: embed.description = 'Nenhum produto compatível está disponível neste estabelecimento.'
        await ctx.send(embed=embed)

    @loja.command(name='comprar')
    async def comprar(self, ctx, item_id, quantidade: int = 1):
        mercado = await self._mercado(ctx)
        if not mercado: return
        item = self._get_item(item_id)
        if not item: await ctx.send('❌ Item não encontrado.'); return
        if quantidade < 1 or quantidade > item.get('maximo', 99): await ctx.send('❌ Quantidade inválida.'); return
        if not item.get('stackavel', False) and quantidade > 1: await ctx.send('❌ Este item não é stackável.'); return
        if not item.get('stackavel', False) and item_id in self._inventario(str(ctx.author.id), str(ctx.guild.id)): await ctx.send('❌ Você já possui este item.'); return
        produto = self._produto(item); cotacao = self.mercado_economico.cotar(ctx.guild.id, ctx.channel.id, produto, quantidade)
        if 'erro' in cotacao:
            await ctx.send(f"❌ { {'categoria_invalida':'Este produto não pode ser vendido neste estabelecimento.', 'estoque_insuficiente':'Estoque insuficiente.', 'mercado_nao_configurado':'Mercado não configurado.'}.get(cotacao['erro'], 'Erro na cotação.') }"); return
        saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        if saldo < cotacao['preco_total']: await ctx.send(f"❌ Saldo insuficiente. Necessário: {cotacao['preco_total']:,} Hunos."); return
        resultado = self.mercado_economico.comprar(ctx.guild.id, ctx.channel.id, ctx.author.id, produto, quantidade)
        if 'erro' in resultado: await ctx.send('❌ A compra falhou devido à alteração do mercado.'); return
        if not db_hunos.remove_hunos(str(ctx.author.id), str(ctx.guild.id), resultado['preco_total']):
            self.motor.mercados.update_one({'_id': resultado['mercado']['_id']}, {'$inc': {f"estoque.{produto['produto_id']}": quantidade}}); await ctx.send('❌ Erro ao processar o pagamento.'); return
        if not self._adicionar_inventario(str(ctx.author.id), str(ctx.guild.id), item_id, quantidade):
            db_hunos.add_hunos(str(ctx.author.id), str(ctx.guild.id), resultado['preco_total']); self.motor.mercados.update_one({'_id': resultado['mercado']['_id']}, {'$inc': {f"estoque.{produto['produto_id']}": quantidade}}); await ctx.send('❌ Erro ao atualizar inventário. Pagamento revertido.'); return
        embed = discord.Embed(title='✅ Compra realizada', description=f"**{quantidade}x {item['nome']}**", color=discord.Color.green())
        embed.add_field(name='Preço unitário', value=f"{resultado['preco_unitario']:,} Hunos")
        embed.add_field(name='Total', value=f"{resultado['preco_total']:,} Hunos")
        embed.add_field(name='Estoque anterior', value=str(resultado['estoque']))
        embed.add_field(name='Saldo restante', value=f"{saldo - resultado['preco_total']:,} Hunos", inline=False)
        await ctx.send(embed=embed)

    @loja.command(name='usar')
    async def usar(self, ctx, item_id):
        item = self._get_item(item_id)
        if not item: await ctx.send('❌ Item não encontrado.'); return
        inventario = self._inventario(str(ctx.author.id), str(ctx.guild.id))
        if item_id not in inventario: await ctx.send('❌ Você não possui este item no inventário.'); return
        if not self._aplicar_efeito(str(ctx.author.id), str(ctx.guild.id), item):
            await ctx.send('❌ Este item ainda não possui um efeito utilizável pelo sistema.'); return
        if item.get('tipo') == 'consumivel' and not self._remover_inventario(str(ctx.author.id), str(ctx.guild.id), item_id):
            await ctx.send('❌ O efeito foi aplicado, mas ocorreu um erro ao consumir o item.'); return
        await ctx.send(embed=discord.Embed(title='✨ Item utilizado', description=f"Você utilizou **{item['nome']}** com sucesso.", color=discord.Color.green()))

    @loja.command(name='categoria')
    async def categoria(self, ctx, categoria: str):
        mercado = await self._mercado(ctx)
        if not mercado: return
        embed = discord.Embed(title=f'📂 {categoria.capitalize()}', color=discord.Color.gold()); encontrados = 0
        for item in self.itens[:50]:
            if (item.get('categoria') or item.get('tipo', '')).lower() != categoria.lower(): continue
            produto = self._produto(item)
            if not self.mercado_economico.categoria_permitida(mercado, produto['categoria']): continue
            cotacao = self.mercado_economico.cotar(ctx.guild.id, ctx.channel.id, produto)
            if 'erro' not in cotacao:
                embed.add_field(name=item['nome'], value=f"`{item['id']}` — {cotacao['preco_unitario']:,} Hunos", inline=False); encontrados += 1
        if not encontrados: embed.description = 'Nenhum produto desta categoria está disponível neste estabelecimento.'
        await ctx.send(embed=embed)

    @loja.command(name='inventario', aliases=['inv'])
    async def inventario(self, ctx):
        dados = self._inventario(str(ctx.author.id), str(ctx.guild.id))
        if not dados: await ctx.send('📦 Seu inventário está vazio.'); return
        texto = '\n'.join(f"• **{self._get_item(i)['nome'] if self._get_item(i) else i}** x{q}" for i, q in dados.items())
        await ctx.send(embed=discord.Embed(title=f'📦 Inventário de {ctx.author.display_name}', description=texto[:4000], color=discord.Color.blue()))

async def setup(bot):
    await bot.add_cog(Loja(bot))