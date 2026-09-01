import discord
import json
from discord.ext import commands
from database.python.mongodb import db
from database.python.luta import (
    GOLPES,
    MONSTROS,
    obter_jogador,
    pode_lutar,
    criar_participante_jogador,
    criar_monstro,
    calcular_dano,
    finalizar_combate
)
import random
import asyncio

with open('database/json/monstros.json', 'r', encoding= 'utf-8') as f:
     rec = json.load(f)

class Luta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.combates = {}

    @commands.group(name="luta", aliases=["fight"], invoke_without_command=True)
    async def luta(self, ctx):
        embed = discord.Embed(
            title="⚔️ Sistema de Luta",
            color=discord.Color.red()
        )
        embed.add_field(
            name="📋 Comandos",
            value=(
                "`!luta pve <monstro>` - Lutar\n"
                "`!luta monstros` - Ver monstros\n"
                "`!soco` - Soco\n"
                "`!chute` - Chute\n"
                "`!defesa` - Defender\n"
                "`!esquiva` - Esquivar\n"
                "`!fugir` - Fugir\n"
                "`!rluta` - Resetar situação de combate"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @luta.command(name="monstros")
    async def luta_monstros(self, ctx):
        embed = discord.Embed(title="🐉 Monstros", color=discord.Color.dark_red())
        for id_monstro, dados in list(MONSTROS.items())[:10]:
            embed.add_field(
                name=f"{dados['emoji']} {dados['nome']}",
                value=(
                    f"**Vida:** {dados['vida_base']}\n"
                    f"**Dano:** {dados['dano_base']}\n"
                    f"**XP:** {dados['xp_recompensa']}\n"
                    f"**Hunos:** {dados['hunos_recompensa']}"
                ),
                inline=True
            )
        await ctx.send(embed=embed)

    @luta.command(name="pve")
    async def luta_pve(self, ctx, monstro_tipo: str):
        """Inicia luta contra um monstro - VERSÃO SIMPLIFICADA"""
        try:
            # Verifica se o monstro existe
            if monstro_tipo not in MONSTROS:
                await ctx.send(f"❌ Monstro `{monstro_tipo}` não encontrado.")
                return
            
            # Verifica se já tem batalha
            if ctx.channel.id in self.combates:
                await ctx.send("❌ Já há uma batalha ativa neste canal.")
                return
            
            # Verifica se pode lutar
            verificacao = pode_lutar(str(ctx.author.id), str(ctx.guild.id))
            if not verificacao["pode"]:
                await ctx.send(f"❌ {verificacao['mensagem']}")
                return
            
            # Pega os dados do jogador DIRETAMENTE do MongoDB
            jogador_data = db["Jogadores"].find_one({
                "ID": str(ctx.author.id),
                "guild_id": str(ctx.guild.id)
            })
            
            if not jogador_data:
                await ctx.send("❌ Você não está registrado.")
                return
            
            # Cria o participante jogador MANUALMENTE
            forca = jogador_data.get("Força", 10)
            defesa = jogador_data.get("Defesa", 10)
            defesa_total = (forca + defesa) * 2
            
            jogador = {
                "id": str(ctx.author.id),
                "nome": jogador_data.get("Nome", ctx.author.display_name),
                "tipo": "jogador",
                "vida": jogador_data.get("Vida", 100),
                "vida_maxima": jogador_data.get("Vida_Maxima", 100),
                "mana": jogador_data.get("Mana", 50),
                "velocidade": jogador_data.get("Velocidade", 50),
                "defesa": defesa_total,
                "Força": forca,
                "Destreza": jogador_data.get("Destreza", 10),
                "defesa_ativa": False,
                "esquiva_ativa": False
            }
            
            # Cria o monstro
            monstro = criar_monstro(monstro_tipo, 1)
            if not monstro:
                await ctx.send(f"❌ Erro ao criar monstro.")
                return
            
            # Ordena por velocidade
            participantes = [jogador, monstro]
            participantes.sort(key=lambda x: x.get("velocidade", 0), reverse=True)
            
            # Salva o combate
            self.combates[ctx.channel.id] = {
                "participantes": participantes,
                "turno": 0,
                "ativo": True,
                "guild_id": str(ctx.guild.id),
                "pvp": False,
                "historico": []
            }
            
            # Atualiza situação no MongoDB
            db["Jogadores"].update_one(
                {"ID": str(ctx.author.id), "guild_id": str(ctx.guild.id)},
                {"$set": {"Situação": "ativo_combate"}}
            )
            
            # Mostra o início
            embed = discord.Embed(
                title=f"⚔️ Batalha contra {monstro['emoji']} {monstro['nome']}",
                description=f"**{participantes[0]['nome']}** começa!",
                color=discord.Color.red()
            )
            
            texto = ""
            for p in participantes:
                if p["tipo"] == "jogador":
                    texto += f"👤 {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']} | 💙 {p['mana']}\n"
                else:
                    texto += f"{p['emoji']} {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']}\n"
            
            embed.add_field(name="📋 Participantes", value=texto, inline=False)
            embed.set_footer(text="Use !soco, !chute, !defesa, !esquiva ou !fugir")
            
            await ctx.send(embed=embed)
            
            # Se o monstro começar, ataca
            if participantes[0]["tipo"] == "monstro":
                await self._turno_monstro(ctx)
                
        except Exception as e:
            await ctx.send(f"❌ Erro ao iniciar batalha: {str(e)}")
            import traceback
            traceback.print_exc()

    # ==========================================
    # TURNO DO MONSTRO
    # ==========================================

    async def _turno_monstro(self, ctx):
        if ctx.channel.id not in self.combates:
            return
        
        combate = self.combates[ctx.channel.id]
        if not combate["ativo"]:
            return
        
        participantes = combate["participantes"]
        participantes = [p for p in participantes if p["vida"] > 0]
        combate["participantes"] = participantes
        
        # VERIFICA SE ACABOU
        jogadores = [p for p in participantes if p["tipo"] == "jogador" and p["vida"] > 0]
        monstros = [p for p in participantes if p["tipo"] == "monstro" and p["vida"] > 0]
        
        if not jogadores or not monstros:
            combate["ativo"] = False
            await self._finalizar(ctx)
            return
        
        if combate["turno"] >= len(participantes):
            combate["turno"] = 0
        
        atual = participantes[combate["turno"] % len(participantes)]
        
        if atual["tipo"] != "monstro":
            return
        
        alvo = random.choice(jogadores)
        dano, tipo = calcular_dano(atual, alvo)
        
        if tipo == "esquivou":
            msg = f"💨 {alvo['nome']} esquivou do ataque de {atual['nome']}!"
        else:
            alvo["vida"] = max(0, alvo["vida"] - dano)
            msg = f"{atual['emoji']} {atual['nome']} atacou {alvo['nome']} causando **{dano}** de dano!"
            
            if alvo["vida"] <= 0:
                msg += f"\n💀 **{alvo['nome']} foi derrotado!**"
        
        combate["historico"].append(msg)
        participantes = [p for p in participantes if p["vida"] > 0]
        combate["participantes"] = participantes
        
        # VERIFICA SE ACABOU
        jogadores = [p for p in participantes if p["tipo"] == "jogador" and p["vida"] > 0]
        monstros = [p for p in participantes if p["tipo"] == "monstro" and p["vida"] > 0]
        
        if not jogadores or not monstros:
            combate["ativo"] = False
            await self._finalizar(ctx)
            return
        
        combate["turno"] += 1
        if combate["turno"] >= len(participantes):
            combate["turno"] = 0
        
        embed = discord.Embed(
            title="⚔️ Ataque do Monstro",
            description=msg,
            color=discord.Color.orange()
        )
        
        texto = ""
        for p in participantes:
            if p["tipo"] == "jogador":
                texto += f"👤 {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']}\n"
            else:
                texto += f"{p['emoji']} {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']}\n"
        
        embed.add_field(name="📋 Status", value=texto, inline=False)
        
        proximo = participantes[combate["turno"] % len(participantes)]
        embed.set_footer(text=f"🔄 Próximo: {proximo['nome']}")
        
        await ctx.send(embed=embed)
        
        if proximo["tipo"] == "monstro" and combate["ativo"]:
            await asyncio.sleep(0.5)
            await self._turno_monstro(ctx)

    # ==========================================
    # AÇÃO DO JOGADOR
    # ==========================================

    async def _acao_jogador(self, ctx, acao: str):
        if ctx.channel.id not in self.combates:
            await ctx.send("❌ Não há batalha ativa.")
            return
        
        combate = self.combates[ctx.channel.id]
        if not combate["ativo"]:
            await ctx.send("❌ Batalha já terminou.")
            return
        
        participantes = combate["participantes"]
        participantes = [p for p in participantes if p["vida"] > 0]
        combate["participantes"] = participantes
        
        # VERIFICA SE ACABOU
        jogadores = [p for p in participantes if p["tipo"] == "jogador" and p["vida"] > 0]
        monstros = [p for p in participantes if p["tipo"] == "monstro" and p["vida"] > 0]
        
        if not jogadores or not monstros:
            combate["ativo"] = False
            await self._finalizar(ctx)
            return
        
        if combate["turno"] >= len(participantes):
            combate["turno"] = 0
        
        atual = participantes[combate["turno"] % len(participantes)]
        
        if atual["tipo"] != "jogador":
            await ctx.send(f"⏳ É a vez de **{atual['nome']}**.")
            return
        
        if atual["id"] != str(ctx.author.id):
            await ctx.send(f"❌ Não é sua vez! É a vez de **{atual['nome']}**.")
            return
        
        # DEFESA
        if acao == "defesa":
            atual["defesa_ativa"] = True
            atual["esquiva_ativa"] = False
            msg = f"🛡️ {atual['nome']} usou Defesa!"
            combate["historico"].append(msg)
            
            combate["turno"] += 1
            if combate["turno"] >= len(participantes):
                combate["turno"] = 0
            
            embed = discord.Embed(
                title="🛡️ Defesa",
                description=msg,
                color=discord.Color.blue()
            )
            
            texto = ""
            for p in participantes:
                if p["tipo"] == "jogador":
                    texto += f"👤 {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']}\n"
                else:
                    texto += f"{p['emoji']} {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']}\n"
            
            embed.add_field(name="📋 Status", value=texto, inline=False)
            proximo = participantes[combate["turno"] % len(participantes)]
            embed.set_footer(text=f"🔄 Próximo: {proximo['nome']}")
            
            await ctx.send(embed=embed)
            
            if proximo["tipo"] == "monstro" and combate["ativo"]:
                await asyncio.sleep(0.5)
                await self._turno_monstro(ctx)
            return
        
        # ESQUIVA
        if acao == "esquiva":
            atual["esquiva_ativa"] = True
            atual["defesa_ativa"] = False
            msg = f"💨 {atual['nome']} tentou Esquiva!"
            combate["historico"].append(msg)
            
            combate["turno"] += 1
            if combate["turno"] >= len(participantes):
                combate["turno"] = 0
            
            embed = discord.Embed(
                title="💨 Esquiva",
                description=msg,
                color=discord.Color.purple()
            )
            
            texto = ""
            for p in participantes:
                if p["tipo"] == "jogador":
                    texto += f"👤 {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']}\n"
                else:
                    texto += f"{p['emoji']} {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']}\n"
            
            embed.add_field(name="📋 Status", value=texto, inline=False)
            proximo = participantes[combate["turno"] % len(participantes)]
            embed.set_footer(text=f"🔄 Próximo: {proximo['nome']}")
            
            await ctx.send(embed=embed)
            
            if proximo["tipo"] == "monstro" and combate["ativo"]:
                await asyncio.sleep(0.5)
                await self._turno_monstro(ctx)
            return
        
        # FUGIR
        if acao == "fugir":
            if random.random() < 0.15:
                combate["ativo"] = False
                atual["mana"] = int(atual["mana"] * 0.5)
                db["Jogadores"].update_one(
                    {"ID": atual["id"], "guild_id": combate["guild_id"]},
                    {"$set": {"Situação": "ativo", "Mana": atual["mana"]}}
                )
                
                embed = discord.Embed(
                    title="🏃 Fuga!",
                    description=f"{atual['nome']} fugiu! (Perdeu 50% da mana)",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                del self.combates[ctx.channel.id]
                return
            else:
                msg = f"{atual['nome']} tentou fugir, mas falhou!"
                combate["historico"].append(msg)
                
                combate["turno"] += 1
                if combate["turno"] >= len(participantes):
                    combate["turno"] = 0
                
                embed = discord.Embed(
                    title="🏃 Fuga Falhou",
                    description=msg,
                    color=discord.Color.red()
                )
                
                proximo = participantes[combate["turno"] % len(participantes)]
                embed.set_footer(text=f"🔄 Próximo: {proximo['nome']}")
                
                await ctx.send(embed=embed)
                
                if proximo["tipo"] == "monstro" and combate["ativo"]:
                    await asyncio.sleep(0.5)
                    await self._turno_monstro(ctx)
                return
        
        # ATAQUE
        golpe = GOLPES.get(acao)
        if not golpe:
            await ctx.send(f"❌ Ação {acao} não encontrada.")
            return
        
        alvos = [p for p in participantes if p["tipo"] == "monstro" and p["vida"] > 0]
        if not alvos:
            await ctx.send("❌ Não há monstros vivos.")
            return
        
        alvo = alvos[0]
        dano, tipo = calcular_dano(atual, alvo)
        
        if tipo == "esquivou":
            msg = f"💨 {alvo['nome']} esquivou do seu {golpe['nome']}!"
        else:
            alvo["vida"] = max(0, alvo["vida"] - dano)
            msg = f"{atual['nome']} usou **{golpe['nome']}** em {alvo['nome']} causando **{dano}** de dano!"
            if alvo["vida"] <= 0:
                msg += f"\n💀 **{alvo['nome']} foi derrotado!**"
        
        combate["historico"].append(msg)
        participantes = [p for p in participantes if p["vida"] > 0]
        combate["participantes"] = participantes
        
        # VERIFICA SE ACABOU
        jogadores = [p for p in participantes if p["tipo"] == "jogador" and p["vida"] > 0]
        monstros = [p for p in participantes if p["tipo"] == "monstro" and p["vida"] > 0]
        
        if not jogadores or not monstros:
            combate["ativo"] = False
            await self._finalizar(ctx)
            return
        
        combate["turno"] += 1
        if combate["turno"] >= len(participantes):
            combate["turno"] = 0
        
        embed = discord.Embed(
            title=f"⚔️ {golpe['nome']}!",
            description=msg,
            color=discord.Color.blue()
        )
        
        texto = ""
        for p in participantes:
            if p["tipo"] == "jogador":
                texto += f"👤 {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']}\n"
            else:
                texto += f"{p['emoji']} {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']}\n"
        
        embed.add_field(name="📋 Status", value=texto, inline=False)
        proximo = participantes[combate["turno"] % len(participantes)]
        embed.set_footer(text=f"🔄 Próximo: {proximo['nome']}")
        
        await ctx.send(embed=embed)
        
        if proximo["tipo"] == "monstro" and combate["ativo"]:
            await asyncio.sleep(0.5)
            await self._turno_monstro(ctx)

    # ==========================================
    # FINALIZAR
    # ==========================================
    
    async def _finalizar(self, ctx, embed=None):
        xpp = rec.get("xp_recompensa")
        hunosp = rec.get("hunos_recompensa")
    # """Finaliza a batalha e mostra as recompensas"""
        if ctx.channel.id not in self.combates:
            return
        combate = self.combates[ctx.channel.id]
        recompensas = finalizar_combate(combate)
        # Cria o embed se não foi passado
        if embed is None:
            embed = discord.Embed(
        title="🏆 Batalha Finalizada!",
        color=discord.Color.green())
        else:
            embed.title = "🏆 Batalha Finalizada!"
            embed.color = discord.Color.green()
        # ==========================================
        # STATUS FINAL DOS PARTICIPANTES
        # ==========================================
        texto_status = ""
        for p in combate["participantes"]:
            if p["tipo"] == "jogador":
                status = "❤️ Vivo" if p["vida"] > 0 else "💀 Morto"
                texto_status += f"👤 **{p['nome']}** - {status} ({p['vida']}/{p['vida_maxima']})\n"
            else:
                status = "❤️ Vivo" if p["vida"] > 0 else "💀 Morto"
                texto_status += f"{p['emoji']} **{p['nome']}** (Nv. {p.get('nivel', 1)}) - {status} ({p['vida']}/{p['vida_maxima']})\n"
        embed.add_field(name="📋 Status Final", value=texto_status, inline=False)
        # ==========================================
        # RECOMPENSAS
        # ==========================================
        if recompensas:
            # Busca os nomes dos monstros derrotados
            monstros_derrotados = [p for p in combate["participantes"] if p["tipo"] == "monstro" and p["vida"] <= 0]
            texto_monstros = ""
            for monstro in monstros_derrotados:
                texto_monstros += f"{monstro['emoji']} {monstro['nome']} (Nv. {monstro.get('nivel', 1)})\n"
            embed.add_field(
                name="🎁 Recompensas",
                value=(
            f"**XP:** +{xpp}\n"
            f"**Hunos:** +{hunosp}\n\n"
            f"**Monstros Derrotados:**\n{texto_monstros if texto_monstros else 'Nenhum'}"
        ),
        inline=False)
            # Adiciona um campo com o total de ganhos
            total_ganhos = recompensas['xp'] + recompensas['hunos']
            embed.add_field(
        name="📊 Total de Ganhos",
        value=f"**{total_ganhos}** pontos combinados (XP + Hunos)",
        inline=False
    )    
        else:
            # Verifica se todos os jogadores morreram
            jogadores_vivos = [p for p in combate["participantes"] if p["tipo"] == "jogador" and p["vida"] > 0]
            if not jogadores_vivos:
                embed.add_field(
            name="💀 Fim da Jornada",
            value="Todos os jogadores foram derrotados!",
            inline=False
        )
            else:
                embed.add_field(
            name="⚠️ Sem Recompensas",
            value="Nenhum monstro foi derrotado.",
            inline=False
        )

        # ==========================================
        # HISTÓRICO DA BATALHA
        # ==========================================
        if combate.get("historico"):
            historico_texto = "\n".join(combate["historico"][-5:])
            embed.add_field(
        name="📜 Últimas Ações",
        value=historico_texto if historico_texto else "Nenhuma ação registrada.",
        inline=False
                        )
        # ==========================================
        # ESTATÍSTICAS DA BATALHA
        # ==========================================
        total_rodadas = combate.get("rodada", 0) + 1
        total_acoes = len(combate.get("historico", []))
    
        embed.add_field(
    name="📊 Estatísticas da Batalha",
    value=(
        f"**Rodadas:** {total_rodadas}\n"
        f"**Ações:** {total_acoes}\n"
        f"**Participantes:** {len(combate['participantes'])}"
    ),
    inline=False
)
    #
    ## ==========================================
    ## RODAPÉ
    ## ==========================================
        embed.set_footer(text="Moon Tensura • Korczak Technologies")

        # Remove o combate da memória
        del self.combates[ctx.channel.id]

        await ctx.send(embed=embed)

    # ==========================================
    # COMANDO RESETAR LUTA
    # ==========================================

    @commands.command(name="rluta")
    async def rluta(self, ctx):
        """Reseta a situação de combate do jogador"""
        try:
            # Verifica se o jogador está em combate
            jogador = db["Jogadores"].find_one({
                "ID": str(ctx.author.id),
                "guild_id": str(ctx.guild.id)
            })
            
            if not jogador:
                await ctx.send("❌ Você não está registrado.")
                return
            
            situacao = jogador.get("Situação", "")
            
            if situacao != "ativo_combate":
                await ctx.send("✅ Você já não está em combate.")
                return
            
            # Reseta a situação
            db["Jogadores"].update_one(
                {"ID": str(ctx.author.id), "guild_id": str(ctx.guild.id)},
                {"$set": {"Situação": "ativo"}}
            )
            
            # Verifica se havia um combate ativo no canal e remove
            if ctx.channel.id in self.combates:
                combate = self.combates[ctx.channel.id]
                # Remove o jogador do combate
                combate["participantes"] = [p for p in combate["participantes"] if p["id"] != str(ctx.author.id)]
                
                # Se não sobrar ninguém ou só monstros, remove o combate
                if not combate["participantes"] or all(p["tipo"] != "jogador" for p in combate["participantes"]):
                    combate["ativo"] = False
                    del self.combates[ctx.channel.id]
            
            embed = discord.Embed(
                title="✅ Combate Resetado!",
                description=f"{ctx.author.mention}, sua situação de combate foi resetada.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="📋 Status",
                value="**Situação:** ativo",
                inline=False
            )
            embed.set_footer(text="Agora você pode usar outros comandos normalmente.")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Erro ao resetar combate: {str(e)}")
            print(f"Erro em rluta: {e}")

    # ==========================================
    # COMANDO DE TESTE
    # ==========================================

    @commands.command(name="testpve")
    async def testpve(self, ctx):
        """Comando de teste para debug do PvE"""
        try:
            await ctx.send("🔍 Iniciando teste PvE...")
            
            # Testa 1: Verifica se MONSTROS está carregado
            await ctx.send(f"📊 MONSTROS carregado: {len(MONSTROS)} monstros")
            if MONSTROS:
                await ctx.send(f"📋 Monstros disponíveis: {', '.join(list(MONSTROS.keys())[:5])}")
            
            # Testa 2: Verifica se o jogador existe
            jogador = obter_jogador(str(ctx.author.id), str(ctx.guild.id))
            if jogador:
                await ctx.send(f"✅ Jogador encontrado: {jogador.get('Nome', 'Sem nome')}")
            else:
                await ctx.send("❌ Jogador NÃO encontrado!")
                return
            
            # Testa 3: Verifica se pode lutar
            verificacao = pode_lutar(str(ctx.author.id), str(ctx.guild.id))
            await ctx.send(f"🔍 Pode lutar: {verificacao}")
            
            # Testa 4: Tenta criar participante
            participante = criar_participante_jogador(str(ctx.author.id), str(ctx.guild.id))
            if participante:
                await ctx.send(f"✅ Participante criado: {participante['nome']} - Vida: {participante['vida']}")
            else:
                await ctx.send("❌ Falha ao criar participante!")
                return
            
            # Testa 5: Tenta criar monstro
            monstro = criar_monstro("slime", 1)
            if monstro:
                await ctx.send(f"✅ Monstro criado: {monstro['emoji']} {monstro['nome']} - Vida: {monstro['vida']}")
            else:
                await ctx.send("❌ Falha ao criar monstro!")
                return
            
            await ctx.send("✅ Todos os testes passaram! O sistema PvE deve funcionar.")
            
        except Exception as e:
            await ctx.send(f"❌ Erro no teste: {str(e)}")
            import traceback
            traceback.print_exc()

    # ==========================================
    # COMANDOS
    # ==========================================

    @commands.command(name="soco")
    async def soco(self, ctx):
        await self._acao_jogador(ctx, "soco")

    @commands.command(name="chute")
    async def chute(self, ctx):
        await self._acao_jogador(ctx, "chute")

    @commands.command(name="defesa")
    async def defesa(self, ctx):
        await self._acao_jogador(ctx, "defesa")

    @commands.command(name="esquiva")
    async def esquiva(self, ctx):
        await self._acao_jogador(ctx, "esquiva")

    @commands.command(name="fugir")
    async def fugir(self, ctx):
        await self._acao_jogador(ctx, "fugir")

async def setup(bot):
    await bot.add_cog(Luta(bot))