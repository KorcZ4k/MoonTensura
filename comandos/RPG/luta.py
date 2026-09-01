import discord
from discord.ext import commands
from database.python.mongodb import db
from database.python.luta import (
    GOLPES,
    MONSTROS,
    obter_jogador,
    pode_lutar,
    iniciar_combate,
    executar_acao,
    fugir,
    criar_monstro,
    calcular_dano
)
import json

class Luta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.combates = {}  # {guild_id: {channel_id: combate_data}}

    @commands.group(name="luta", aliases=["fight", "batalha"], invoke_without_command=True)
    async def luta(self, ctx):
        """Comando principal de luta"""
        embed = discord.Embed(
            title="⚔️ Sistema de Luta",
            description="Entre em combate contra monstros ou outros jogadores!",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="📋 Comandos",
            value=(
                "**PvE:**\n"
                "`!luta pve <monstro> [nivel]` - Lutar contra um monstro\n"
                "`!luta pve party <@membro1> <@membro2> ...` - Lutar em party\n"
                "`!luta monstros` - Ver monstros disponíveis\n\n"
                "**PvP:**\n"
                "`!luta pvp @jogador` - Desafiar um jogador\n\n"
                "**Durante a batalha:**\n"
                "`!soco [@alvo]` - Soco básico\n"
                "`!chute [@alvo]` - Chute poderoso\n"
                "`!golpepesado [@alvo]` - Golpe pesado (custa mana)\n"
                "`!golperapido [@alvo]` - Golpe rápido (custa mana)\n"
                "`!golpemagico [@alvo]` - Golpe mágico (custa mana)\n"
                "`!golpesupremo [@alvo]` - Golpe supremo (custa mana)\n"
                "`!defesa` - Se defender\n"
                "`!esquiva` - Tentar esquivar\n"
                "`!fugir` - Tentar fugir (15% de chance)\n"
                "`!status` - Ver status durante a batalha"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

    @luta.command(name="monstros")
    async def luta_monstros(self, ctx):
        """Mostra os monstros disponíveis"""
        embed = discord.Embed(
            title="🐉 Monstros Disponíveis",
            description="Escolha um monstro para lutar!",
            color=discord.Color.dark_red()
        )
        
        for id_monstro, dados in MONSTROS.items():
            embed.add_field(
                name=f"{dados['emoji']} {dados['nome']}",
                value=(
                    f"**Vida:** {dados['vida']}\n"
                    f"**Dano:** {dados['dano_base']}\n"
                    f"**Defesa:** {dados['defesa']}\n"
                    f"**Velocidade:** {dados['velocidade']}\n"
                    f"**XP:** {dados['xp_recompensa']}\n"
                    f"**Hunos:** {dados['hunos_recompensa']}\n"
                    f"**Nível Mínimo:** {dados.get('nivel_minimo', 1)}"
                ),
                inline=True
            )
        
        await ctx.send(embed=embed)

    @luta.command(name="pve")
    async def luta_pve(self, ctx, monstro_tipo: str, nivel: int = 1):
        """Inicia uma luta PvE contra um monstro"""
        if monstro_tipo not in MONSTROS:
            await ctx.send(f"❌ Monstro `{monstro_tipo}` não encontrado.")
            return
        
        # Verifica se o jogador pode lutar
        verificacao = pode_lutar(str(ctx.author.id), str(ctx.guild.id))
        if not verificacao["pode"]:
            await ctx.send(f"❌ {verificacao['mensagem']}")
            return
        
        # Verifica nível mínimo
        dados_monstro = MONSTROS[monstro_tipo]
        jogador = obter_jogador(str(ctx.author.id), str(ctx.guild.id))
        nivel_jogador = jogador.get("Nivel", 1)
        
        if nivel_jogador < dados_monstro.get("nivel_minimo", 1):
            await ctx.send(f"❌ Você precisa ser nível {dados_monstro['nivel_minimo']} para lutar contra {dados_monstro['nome']}.")
            return
        
        # Cria o monstro
        monstro = criar_monstro(monstro_tipo, nivel)
        
        # Inicia o combate
        combate = iniciar_combate(
            [str(ctx.author.id)],
            str(ctx.guild.id),
            [{"tipo": monstro_tipo, "nivel": nivel}],
            pvp=False
        )
        
        # Salva o combate
        key = f"{ctx.guild.id}_{ctx.channel.id}"
        self.combates[key] = combate
        
        # Atualiza situação do jogador
        db["Jogadores"].update_one(
            {"ID": str(ctx.author.id), "guild_id": str(ctx.guild.id)},
            {"$set": {"Situação": "ativo_combate"}}
        )
        
        # Mostra o início da batalha
        embed = discord.Embed(
            title=f"⚔️ Batalha contra {monstro['emoji']} {monstro['nome']} (Nv. {nivel})",
            description="A batalha começou! Use seus golpes para derrotar o monstro.",
            color=discord.Color.red()
        )
        
        # Mostra os participantes
        texto_participantes = ""
        for p in combate["participantes"]:
            if p["tipo"] == "jogador":
                texto_participantes += f"👤 {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']} | 💙 {p['mana']}/{p['mana_maxima']}\n"
            else:
                texto_participantes += f"{p['emoji']} {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']}\n"
        
        embed.add_field(name="📋 Participantes", value=texto_participantes, inline=False)
        embed.add_field(name="🔄 Turno", value=f"**{combate['participantes'][combate['turno_atual']]['nome']}**", inline=False)
        embed.set_footer(text="Use !ajuda para ver os comandos de batalha")
        
        await ctx.send(embed=embed)

    @luta.command(name="pvp")
    async def luta_pvp(self, ctx, alvo: discord.Member):
        """Desafia um jogador para PvP"""
        if alvo == ctx.author:
            await ctx.send("❌ Você não pode lutar contra si mesmo!")
            return
        
        if alvo.bot:
            await ctx.send("❌ Você não pode lutar contra um bot!")
            return
        
        # Verifica se o jogador pode lutar
        verificacao = pode_lutar(str(ctx.author.id), str(ctx.guild.id))
        if not verificacao["pode"]:
            await ctx.send(f"❌ {verificacao['mensagem']}")
            return
        
        verificacao_alvo = pode_lutar(str(alvo.id), str(ctx.guild.id))
        if not verificacao_alvo["pode"]:
            await ctx.send(f"❌ {alvo.mention} não pode lutar: {verificacao_alvo['mensagem']}")
            return
        
        # Inicia o combate
        combate = iniciar_combate(
            [str(ctx.author.id), str(alvo.id)],
            str(ctx.guild.id),
            monstros=None,
            pvp=True
        )
        
        # Salva o combate
        key = f"{ctx.guild.id}_{ctx.channel.id}"
        self.combates[key] = combate
        
        # Atualiza situação dos jogadores
        for user_id in [str(ctx.author.id), str(alvo.id)]:
            db["Jogadores"].update_one(
                {"ID": user_id, "guild_id": str(ctx.guild.id)},
                {"$set": {"Situação": "ativo_combate"}}
            )
        
        # Mostra o início da batalha
        embed = discord.Embed(
            title=f"⚔️ Batalha PvP: {ctx.author.display_name} vs {alvo.display_name}",
            description="A batalha começou! Que vença o melhor!",
            color=discord.Color.gold()
        )
        
        texto_participantes = ""
        for p in combate["participantes"]:
            texto_participantes += f"👤 {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']} | 💙 {p['mana']}/{p['mana_maxima']}\n"
        
        embed.add_field(name="📋 Participantes", value=texto_participantes, inline=False)
        embed.add_field(name="🔄 Turno", value=f"**{combate['participantes'][combate['turno_atual']]['nome']}**", inline=False)
        embed.set_footer(text="Use !ajuda para ver os comandos de batalha")
        
        await ctx.send(embed=embed)

    # ==========================================
    # COMANDOS DE BATALHA
    # ==========================================

    async def _executar_acao_batalha(self, ctx, acao: str, alvo: discord.Member = None):
        """Executa uma ação na batalha atual"""
        key = f"{ctx.guild.id}_{ctx.channel.id}"
        
        if key not in self.combates:
            await ctx.send("❌ Não há uma batalha ativa neste canal.")
            return
        
        combate = self.combates[key]
        
        if not combate["ativo"]:
            await ctx.send("❌ Esta batalha já terminou.")
            return
        
        # Verifica se é a vez do jogador
        participante_atual = combate["participantes"][combate["turno_atual"]]
        if participante_atual["id"] != str(ctx.author.id):
            await ctx.send(f"❌ Não é sua vez! É a vez de **{participante_atual['nome']}**.")
            return
        
        # Verifica se o alvo está no combate
        alvo_id = None
        if alvo:
            # Verifica se o alvo é um jogador
            for p in combate["participantes"]:
                if p["tipo"] == "jogador" and p["id"] == str(alvo.id):
                    alvo_id = p["id"]
                    break
                elif p["tipo"] == "monstro" and p["nome"].lower() == alvo.display_name.lower():
                    alvo_id = p["id"]
                    break
            
            if not alvo_id:
                await ctx.send("❌ Alvo não encontrado no combate.")
                return
        
        # Se não especificou alvo e tem 2 participantes, ataca o outro
        if not alvo_id and len(combate["participantes"]) == 2:
            for p in combate["participantes"]:
                if p["id"] != str(ctx.author.id):
                    alvo_id = p["id"]
                    break
        
        # Executa a ação
        resultado = executar_acao(combate, str(ctx.author.id), acao, alvo_id)
        
        if not resultado["sucesso"]:
            await ctx.send(f"❌ {resultado['mensagem']}")
            return
        
        # Mostra o resultado
        embed = discord.Embed(
            title="⚔️ Batalha",
            description=resultado["mensagem"],
            color=discord.Color.red()
        )
        
        # Mostra o histórico (últimas 5 ações)
        historico = resultado.get("historico", [])
        if historico:
            ultimas = historico[-5:]
            embed.add_field(
                name="📜 Histórico",
                value="\n".join(ultimas),
                inline=False
            )
        
        # Mostra os participantes
        participantes_texto = ""
        for p in combate["participantes"]:
            if p["tipo"] == "jogador":
                participantes_texto += f"👤 {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']} | 💙 {p['mana']}/{p['mana_maxima']}\n"
            else:
                participantes_texto += f"{p.get('emoji', '👾')} {p['nome']} - ❤️ {p['vida']}/{p['vida_maxima']}\n"
        
        embed.add_field(name="📋 Status", value=participantes_texto, inline=False)
        
        # Verifica se o combate terminou
        if resultado.get("combate_terminou", False):
            embed.color = discord.Color.green()
            embed.title = "🏆 Batalha Finalizada!"
            embed.description = "A batalha chegou ao fim!"
            
            # Remove o combate
            del self.combates[key]
            
            # Atualiza situação dos jogadores
            for p in combate["participantes"]:
                if p["tipo"] == "jogador":
                    db["Jogadores"].update_one(
                        {"ID": p["id"], "guild_id": str(ctx.guild.id)},
                        {"$set": {"Situação": "ativo"}}
                    )
            
            # Recompensas para PvE
            if not combate["pvp"]:
                jogadores_vivos = [p for p in combate["participantes"] if p["tipo"] == "jogador" and p["vida"] > 0]
                if jogadores_vivos:
                    # Calcula recompensas
                    xp_total = 0
                    hunos_total = 0
                    for p in combate["participantes"]:
                        if p["tipo"] == "monstro" and p["vida"] <= 0:
                            xp_total += p.get("xp_recompensa", 0)
                            hunos_total += p.get("hunos_recompensa", 0)
                    
                    if xp_total > 0 or hunos_total > 0:
                        embed.add_field(
                            name="🎁 Recompensas",
                            value=f"**XP:** +{xp_total}\n**Hunos:** +{hunos_total}",
                            inline=False
                        )
                        
                        # Aplica as recompensas ao jogador
                        for p in jogadores_vivos:
                            db["Jogadores"].update_one(
                                {"ID": p["id"], "guild_id": str(ctx.guild.id)},
                                {
                                    "$inc": {
                                        "XP": xp_total,
                                        "Hunos": hunos_total
                                    }
                                }
                            )
        else:
            embed.set_footer(text=f"🔄 Turno: {combate['participantes'][combate['turno_atual']]['nome']} - Rodada {combate['rodada']}")
        
        await ctx.send(embed=embed)

    @commands.command(name="soco")
    async def soco(self, ctx, alvo: discord.Member = None):
        """Dá um soco no alvo"""
        await self._executar_acao_batalha(ctx, "soco", alvo)

    @commands.command(name="chute")
    async def chute(self, ctx, alvo: discord.Member = None):
        """Dá um chute no alvo"""
        await self._executar_acao_batalha(ctx, "chute", alvo)

    @commands.command(name="golpepesado")
    async def golpepesado(self, ctx, alvo: discord.Member = None):
        """Usa golpe pesado no alvo"""
        await self._executar_acao_batalha(ctx, "golpe_pesado", alvo)

    @commands.command(name="golperapido")
    async def golperapido(self, ctx, alvo: discord.Member = None):
        """Usa golpe rápido no alvo"""
        await self._executar_acao_batalha(ctx, "golpe_rapido", alvo)

    @commands.command(name="golpemagico")
    async def golpemagico(self, ctx, alvo: discord.Member = None):
        """Usa golpe mágico no alvo"""
        await self._executar_acao_batalha(ctx, "golpe_magico", alvo)

    @commands.command(name="golpesupremo")
    async def golpesupremo(self, ctx, alvo: discord.Member = None):
        """Usa golpe supremo no alvo"""
        await self._executar_acao_batalha(ctx, "golpe_supremo", alvo)

    @commands.command(name="defesa")
    async def defesa(self, ctx):
        """Se defende do próximo ataque"""
        await self._executar_acao_batalha(ctx, "defesa", None)

    @commands.command(name="esquiva")
    async def esquiva(self, ctx):
        """Tenta esquivar do próximo ataque"""
        await self._executar_acao_batalha(ctx, "esquiva", None)

    @commands.command(name="fugir")
    async def fugir(self, ctx):
        """Tenta fugir da batalha (15% de chance)"""
        key = f"{ctx.guild.id}_{ctx.channel.id}"
        
        if key not in self.combates:
            await ctx.send("❌ Não há uma batalha ativa neste canal.")
            return
        
        combate = self.combates[key]
        
        if not combate["ativo"]:
            await ctx.send("❌ Esta batalha já terminou.")
            return
        
        resultado = fugir(combate, str(ctx.author.id))
        
        embed = discord.Embed(
            title="🏃 Fuga",
            description=resultado["mensagem"],
            color=discord.Color.green() if resultado["fugiu"] else discord.Color.red()
        )
        
        if resultado["fugiu"]:
            # Remove o combate
            del self.combates[key]
            
            # Atualiza situação do jogador
            db["Jogadores"].update_one(
                {"ID": str(ctx.author.id), "guild_id": str(ctx.guild.id)},
                {"$set": {"Situação": "ativo"}}
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Luta(bot))