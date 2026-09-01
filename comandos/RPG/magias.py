import discord
from discord.ext import commands
from database.python.mongodb import db
from database.python.magias import db_magias
import json
import os

class Magias(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.elementos = self._carregar_elementos()
        self.formas = self._carregar_formas()
        print(f"✅ {len(self.elementos)} elementos carregados")
        print(f"✅ {len(self.formas)} formas de magia carregadas")

    def _carregar_elementos(self):
        """Carrega os elementos do JSON"""
        try:
            with open('database/json/magias/elementos.json', 'r', encoding='utf-8') as f:
                dados = json.load(f)
                return dados.get("elementos", [])
        except Exception as e:
            print(f"❌ Erro ao carregar elementos: {e}")
            return []

    def _carregar_formas(self):
        """Carrega as formas de magia do JSON"""
        try:
            with open('database/json/magias/formas.json', 'r', encoding='utf-8') as f:
                dados = json.load(f)
                return dados.get("formas", [])
        except Exception as e:
            print(f"❌ Erro ao carregar formas: {e}")
            return []

    def _get_elemento(self, nome_elemento: str):
        """Busca um elemento pelo nome"""
        for elemento in self.elementos:
            if elemento["nome"].lower() == nome_elemento.lower():
                return elemento
        return None

    def _get_forma(self, id_forma: str):
        """Busca uma forma pelo ID"""
        for forma in self.formas:
            if forma["id"].lower() == id_forma.lower():
                return forma
        return None

    def _criar_barra_afinidade(self, valor: int, tamanho: int = 10):
        """Cria uma barra visual para afinidade"""
        preenchidos = int((valor / 100) * tamanho)
        vazios = tamanho - preenchidos
        return "█" * preenchidos + "░" * vazios

    def _jogador_tem_magia_elemento(self, user_id: int, guild_id: int, elemento: str):
        """Verifica se o jogador tem alguma magia de um elemento específico"""
        if db is None:
            return False
        
        magias_ids = db_magias.get_magias(str(user_id), str(guild_id))
        
        if not magias_ids:
            return False
        
        for magia_item in magias_ids:
            if isinstance(magia_item, dict):
                magia_id = magia_item.get("id", "")
            else:
                magia_id = magia_item
            
            if magia_id.startswith(f"{elemento}_"):
                return True
        
        return False

    @commands.group(name="magias", aliases=["mags", "spells"], invoke_without_command=True)
    async def magias(self, ctx):
        """Comando principal de magias"""
        embed = discord.Embed(
            title="🔮 Sistema de Magias",
            description="Comandos disponíveis para magias",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="📋 Comandos",
            value=(
                "`!magias list` - Mostra suas magias\n"
                "`!magias elementos` - Mostra todos os elementos\n"
                "`!magias formas` - Mostra todas as formas\n"
                "`!usarmagia <elemento> <forma> [@alvo]` - Usa uma magia"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

    @magias.command(name="list", aliases=["lista", "minhas"])
    async def magias_list(self, ctx):
        """Mostra todas as magias do jogador com afinidade"""
        if db is None:
            await ctx.send("❌ Banco de dados não conectado.")
            return

        # Busca as magias do jogador no MongoDB
        magias_ids = db_magias.get_magias(str(ctx.author.id), str(ctx.guild.id))
        
        if not magias_ids:
            await ctx.send("❌ Você não possui nenhuma magia.")
            return

        # Busca a afinidade do jogador
        jogadores = db["Jogadores"]
        jogador = jogadores.find_one({
            "ID": str(ctx.author.id),
            "guild_id": str(ctx.guild.id)
        })
        
        # Pega a afinidade (se existir)
        afinidades = {}
        if jogador and jogador.get("afinidades"):
            afinidades = jogador.get("afinidades", {})

        # Mostra as magias do jogador
        embed = discord.Embed(
            title=f"📖 Grimório de Magias — {ctx.author.display_name}",
            description="Suas magias disponíveis com afinidade",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        # Agrupa por elemento
        magias_por_elemento = {}
        afinidade_por_elemento = {}
        
        for magia_item in magias_ids:
            if isinstance(magia_item, dict):
                magia_id = magia_item.get("id", "")
                tipos = magia_item.get("tipos", [])
            else:
                magia_id = magia_item
                tipos = []
            
            partes = magia_id.split('_')
            if len(partes) == 2:
                elemento_nome, forma_id = partes
                elemento = self._get_elemento(elemento_nome)
                forma = self._get_forma(forma_id)
                
                if elemento and forma:
                    if elemento_nome not in magias_por_elemento:
                        magias_por_elemento[elemento_nome] = []
                        afinidade_por_elemento[elemento_nome] = afinidades.get(elemento_nome, 0)
                    
                    magias_por_elemento[elemento_nome].append({
                        "forma": forma,
                        "elemento": elemento,
                        "tipos": tipos
                    })

        if not magias_por_elemento:
            await ctx.send("❌ Nenhuma magia encontrada no formato correto.")
            return

        # Ordena os elementos por afinidade
        elementos_ordenados = sorted(
            magias_por_elemento.keys(),
            key=lambda e: afinidade_por_elemento.get(e, 0),
            reverse=True
        )

        for elemento_nome in elementos_ordenados:
            magias_lista = magias_por_elemento[elemento_nome]
            elemento = self._get_elemento(elemento_nome)
            emoji = elemento.get("emoji", "✨") if elemento else "✨"
            afinidade = afinidade_por_elemento.get(elemento_nome, 0)
            
            barra = self._criar_barra_afinidade(afinidade)
            titulo = f"{emoji} {elemento_nome.capitalize()} - Afinidade: {afinidade}% {barra}"
            
            texto = ""
            for magia in magias_lista[:15]:
                forma = magia["forma"]
                tipos = magia.get("tipos", [])
                
                tipos_texto = ""
                if tipos:
                    tipos_texto = f" [{', '.join(tipos)}]"
                
                dano_base = forma.get("dano_base", 10)
                if dano_base > 0:
                    dano_afinidade = int(dano_base * (1 + (afinidade / 100)))
                else:
                    dano_afinidade = dano_base
                    
                mana = forma.get("mana_base", 10)
                efeito = forma.get("efeito", {})
                nome_efeito = efeito.get("nome", "Sem efeito")
                
                texto += f"• **{forma['nome']}**{tipos_texto}\n"
                texto += f"  └ Dano: {dano_afinidade} | Mana: {mana} | Efeito: {nome_efeito}\n"
            
            if texto:
                embed.add_field(
                    name=titulo,
                    value=texto,
                    inline=False
                )

        # Adiciona afinidades sem magias
        for elemento_nome, afinidade in afinidades.items():
            if elemento_nome not in magias_por_elemento and afinidade > 0:
                elemento = self._get_elemento(elemento_nome)
                if elemento:
                    emoji = elemento.get("emoji", "✨")
                    barra = self._criar_barra_afinidade(afinidade)
                    embed.add_field(
                        name=f"{emoji} {elemento_nome.capitalize()} - Afinidade: {afinidade}% {barra}",
                        value="*Nenhuma magia deste elemento*",
                        inline=False
                    )

        total_magias = sum(len(m) for m in magias_por_elemento.values())
        embed.set_footer(text=f"Total de magias: {total_magias}")
        await ctx.send(embed=embed)

    @magias.command(name="elementos")
    async def magias_elementos(self, ctx):
        """Mostra todos os elementos disponíveis no sistema"""
        embed = discord.Embed(
            title="✨ Elementos Disponíveis",
            description="Todos os elementos que podem ser usados em magias",
            color=discord.Color.purple()
        )

        # Busca a afinidade do jogador (se existir)
        if db:
            jogadores = db["Jogadores"]
            jogador = jogadores.find_one({
                "ID": str(ctx.author.id),
                "guild_id": str(ctx.guild.id)
            })
            afinidades = jogador.get("afinidades", {}) if jogador else {}
        else:
            afinidades = {}

        # Mostra TODOS os elementos, não apenas os que o jogador tem
        for elemento in self.elementos:
            nome = elemento['nome']
            afinidade = afinidades.get(nome.lower(), 0)
            barra = self._criar_barra_afinidade(afinidade)
            
            # Mostra se o jogador tem magia deste elemento
            tem_magia = self._jogador_tem_magia_elemento(ctx.author.id, ctx.guild.id, nome.lower())
            status_magia = "✅ Tem magia" if tem_magia else "❌ Sem magia"
            
            embed.add_field(
                name=f"{elemento['emoji']} {nome} - Afinidade: {afinidade}% {barra}",
                value=f"{elemento['descricao']}\n{status_magia}",
                inline=False
            )

        embed.set_footer(text=f"Total de elementos: {len(self.elementos)}")
        await ctx.send(embed=embed)

    @magias.command(name="formas")
    async def magias_formas(self, ctx):
        """Mostra todas as formas de magia disponíveis"""
        embed = discord.Embed(
            title="🔮 Formas de Magia",
            description="Formas que podem ser combinadas com elementos",
            color=discord.Color.purple()
        )

        texto = ""
        for forma in self.formas[:25]:
            tipos = forma.get("tipos", [])
            tipos_texto = f"[{', '.join(tipos)}]" if tipos else ""
            efeito = forma.get("efeito", {})
            nome_efeito = efeito.get("nome", "Nenhum")
            texto += f"• **{forma['nome']}** {tipos_texto}\n"
            texto += f"  └ Mana: {forma['mana_base']} | Efeito: {nome_efeito}\n"
        
        embed.add_field(
            name=f"Formas (mostrando 25 de {len(self.formas)})",
            value=texto,
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command(name="usarmagia", aliases=["usarmag", "um"])
    async def usarmagia(self, ctx, elemento: str = None, forma: str = None, *, alvo: discord.Member = None):
        """Usa uma magia
        Uso: !usarmagia fogo bola @alvo
        """
        if elemento is None or forma is None:
            await ctx.send("❌ Uso correto: `!usarmagia <elemento> <forma> [@alvo]`")
            return
        
        if db is None:
            await ctx.send("❌ Banco de dados não conectado.")
            return

        # Verifica se o jogador tem a magia
        magias_ids = db_magias.get_magias(str(ctx.author.id), str(ctx.guild.id))
        
        if not magias_ids:
            await ctx.send("❌ Você não possui nenhuma magia.")
            return

        magia_id = f"{elemento.lower()}_{forma.lower()}"
        
        # Verifica se tem a magia
        tem_magia = False
        tipos_magia = []
        for magia_item in magias_ids:
            if isinstance(magia_item, dict):
                if magia_item.get("id") == magia_id:
                    tem_magia = True
                    tipos_magia = magia_item.get("tipos", [])
                    break
            elif magia_item == magia_id:
                tem_magia = True
                tipos_magia = []
                break
        
        if not tem_magia:
            await ctx.send(f"❌ Você não possui a magia **{forma}** de **{elemento}**.")
            return

        # Busca os dados da magia
        elemento_dados = self._get_elemento(elemento)
        forma_dados = self._get_forma(forma)
        
        if not elemento_dados or not forma_dados:
            await ctx.send("❌ Elemento ou forma inválida.")
            return

        # Busca afinidade do jogador
        jogadores = db["Jogadores"]
        jogador = jogadores.find_one({
            "ID": str(ctx.author.id),
            "guild_id": str(ctx.guild.id)
        })
        
        afinidade = 0
        if jogador and jogador.get("afinidades"):
            afinidade = jogador.get("afinidades", {}).get(elemento.lower(), 0)

        dano_base = forma_dados.get("dano_base", 10)
        if dano_base > 0:
            dano = int(dano_base * (1 + (afinidade / 100)))
        else:
            dano = dano_base
        
        mana = forma_dados.get("mana_base", 10)

        # Verifica mana
        if jogador:
            mana_atual = jogador.get("Mana", 0)
            if mana_atual < mana:
                await ctx.send(f"❌ Mana insuficiente! Você tem {mana_atual:.1f} de mana, precisa de {mana}.")
                return

        # Cria o embed da magia
        embed = discord.Embed(
            title=f"{elemento_dados['emoji']} {forma_dados['nome']} de {elemento_dados['nome']}",
            description=forma_dados['descricao'],
            color=elemento_dados.get('cor', 0x9b59b6)
        )

        embed.add_field(name="Tipo", value=forma_dados.get('tipo', 'Desconhecido'), inline=True)
        embed.add_field(name="Alcance", value=forma_dados.get('alcance', 'Médio'), inline=True)
        embed.add_field(name="Alvo", value=forma_dados.get('alvo', 'Único'), inline=True)
        embed.add_field(name="Dano", value=f"{dano}", inline=True)
        embed.add_field(name="Mana Gasta", value=f"{mana}", inline=True)
        embed.add_field(name="Afinidade", value=f"{afinidade}%", inline=True)
        
        if tipos_magia:
            embed.add_field(
                name="🏷️ Tipos",
                value=f"{', '.join(tipos_magia)}",
                inline=False
            )
        
        efeito = forma_dados.get("efeito", {})
        if efeito:
            nome_efeito = efeito.get("nome", "Desconhecido")
            desc_efeito = efeito.get("descricao", "")
            turnos = efeito.get("turnos", 1)
            valor = efeito.get("valor", 0)
            
            if valor > 0:
                embed.add_field(
                    name="🎯 Efeito",
                    value=f"**{nome_efeito}**\n{desc_efeito}\nDano: {valor} | Turnos: {turnos}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="🎯 Efeito",
                    value=f"**{nome_efeito}**\n{desc_efeito}\nTurnos: {turnos}",
                    inline=False
                )

        if alvo:
            embed.add_field(name="🎯 Alvo", value=alvo.mention, inline=False)
            embed.set_footer(text=f"Lançado por {ctx.author.display_name} contra {alvo.display_name}")
        else:
            embed.set_footer(text=f"Lançado por {ctx.author.display_name}")

        # Consome a mana
        if jogador:
            jogadores.update_one(
                {"ID": str(ctx.author.id), "guild_id": str(ctx.guild.id)},
                {"$inc": {"Mana": -mana}}
            )

        await ctx.send(embed=embed)

    @commands.command(name="addmagia")
    @commands.has_permissions(administrator=True)
    async def addmagia(self, ctx, membro: discord.Member, elemento: str, forma: str):
        """Adiciona uma magia a um jogador (Admin)
        Uso: !addmagia @membro fogo bola
        """
        if db is None:
            await ctx.send("❌ Banco não conectado.")
            return

        # Verifica se o elemento existe
        elemento_dados = self._get_elemento(elemento)
        if not elemento_dados:
            await ctx.send(f"❌ Elemento `{elemento}` não encontrado.")
            return

        # Verifica se a forma existe
        forma_dados = self._get_forma(forma)
        if not forma_dados:
            await ctx.send(f"❌ Forma `{forma}` não encontrada.")
            return

        # Formata o ID da magia
        magia_id = f"{elemento.lower()}_{forma.lower()}"

        # Pega os tipos da forma
        tipos = forma_dados.get("tipos", [])

        # Adiciona a magia com tipos
        sucesso = db_magias.add_magia(
            str(membro.id), 
            str(ctx.guild.id), 
            magia_id, 
            tipos
        )

        if sucesso:
            await ctx.send(f"✅ Magia **{forma}** de **{elemento}** ({', '.join(tipos)}) adicionada a {membro.mention}")
        else:
            await ctx.send("❌ Erro ao adicionar magia.")

    @commands.command(name="removermagia")
    @commands.has_permissions(administrator=True)
    async def removermagia(self, ctx, membro: discord.Member, elemento: str, forma: str):
        """Remove uma magia de um jogador (Admin)
        Uso: !removermagia @membro fogo bola
        """
        if db is None:
            await ctx.send("❌ Banco não conectado.")
            return

        magia_id = f"{elemento.lower()}_{forma.lower()}"

        sucesso = db_magias.remove_magia(
            str(membro.id), 
            str(ctx.guild.id), 
            magia_id
        )

        if sucesso:
            await ctx.send(f"✅ Magia **{forma}** de **{elemento}** removida de {membro.mention}")
        else:
            await ctx.send("❌ Magia não encontrada ou já removida.")

    @commands.command(name="testemagias")
    async def testemagias(self, ctx):
        """Testa as magias do jogador no MongoDB"""
        if db is None:
            await ctx.send("❌ Banco não conectado.")
            return

        magias_collection = db["Magias"]

        doc = magias_collection.find_one({
            "ID": str(ctx.author.id),
            "guild_id": str(ctx.guild.id)
        })

        if not doc:
            await ctx.send("❌ Documento não encontrado na coleção Magias.")
            return

        texto = f"**Documento na coleção Magias:**\n```json\n{json.dumps(doc, indent=2, default=str)[:1900]}\n```"
        await ctx.send(texto)

    @commands.command(name="testemagia")
    async def testemagia(self, ctx):
        """Comando de teste para ver se o cog está carregado"""
        await ctx.send("✅ Comando de magia está funcionando!")

async def setup(bot):
    await bot.add_cog(Magias(bot))