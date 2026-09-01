import discord
from discord.ext import commands
from database.python.mongodb import db
from database.python.Hunos import db_hunos
import random
import asyncio

class Cassino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="cassino", aliases=["casino", "jogar"], invoke_without_command=True)
    async def cassino(self, ctx):
        """Comando principal do cassino"""
        embed = discord.Embed(
            title="🎰 Cassino Moon Tensura",
            description="Jogos de azar para ganhar Hunos!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="🎲 Jogos Disponíveis",
            value=(
                "`!cassino roleta <valor> [numero]` - Roleta (1x - 36x)\n"
                "`!cassino dado <valor>` - Dado (1x - 6x)\n"
                "`!cassino caraoucoroa <valor> [cara/coroa]` - Cara ou Coroa (2x)\n"
                "`!cassino blackjack <valor>` - Blackjack (2x)\n"
                "`!cassino caca-niquel <valor>` - Caça-níquel (até 10x)\n"
                "`!cassino ppt <valor> [pedra/papel/tesoura]` - Pedra Papel Tesoura (2x)\n"
                "`!cassino corrida <valor>` - Corrida de Dados (2x)"
            ),
            inline=False
        )
        
        saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        embed.add_field(
            name="💰 Seu Saldo",
            value=f"{saldo:,} Hunos",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @cassino.command(name="roleta")
    async def cassino_roleta(self, ctx, aposta: int, numero: int = None):
        """Joga na roleta
        Uso: !cassino roleta <valor> [numero]
        """
        if aposta < 1:
            await ctx.send("❌ Aposta mínima: 1 Huno.")
            return
        
        saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        
        if saldo < aposta:
            await ctx.send(f"❌ Saldo insuficiente! Você tem {saldo:,} Hunos.")
            return
        
        # Número sorteado (0-36)
        sorteado = random.randint(0, 36)
        
        if numero is not None:
            if numero < 0 or numero > 36:
                await ctx.send("❌ Número inválido! Escolha entre 0 e 36.")
                return
            
            if sorteado == numero:
                ganho = aposta * 36
                cor = discord.Color.green()
                mensagem = f"🎉 **NÚMERO CERTO!** {sorteado}!"
            else:
                ganho = -aposta
                cor = discord.Color.red()
                mensagem = f"❌ O número sorteado foi **{sorteado}**. Você escolheu **{numero}**."
        else:
            # Aposta em cores (par/ímpar)
            cor_nome = "Par" if sorteado % 2 == 0 and sorteado != 0 else "Ímpar" if sorteado != 0 else "Zero"
            if (sorteado % 2 == 0 and sorteado != 0):
                ganho = aposta
                cor = discord.Color.green()
                mensagem = f"🎉 **{cor_nome}!** Número: {sorteado}"
            elif sorteado == 0:
                ganho = -aposta
                cor = discord.Color.red()
                mensagem = f"❌ **Zero!** Número: {sorteado}"
            else:
                ganho = -aposta
                cor = discord.Color.red()
                mensagem = f"❌ **{cor_nome}!** Número: {sorteado}"
        
        # Atualiza o saldo
        if ganho > 0:
            db_hunos.add_hunos(str(ctx.author.id), str(ctx.guild.id), ganho)
        elif ganho < 0:
            db_hunos.remove_hunos(str(ctx.author.id), str(ctx.guild.id), abs(ganho))
        
        embed = discord.Embed(
            title="🎰 Roleta",
            description=mensagem,
            color=cor
        )
        embed.add_field(name="🎯 Número Sorteado", value=sorteado, inline=True)
        embed.add_field(name="💰 Aposta", value=f"{aposta:,} Hunos", inline=True)
        
        if ganho > 0:
            embed.add_field(name="🎉 Ganho", value=f"+{ganho:,} Hunos", inline=True)
        else:
            embed.add_field(name="💸 Perda", value=f"{abs(ganho):,} Hunos", inline=True)
        
        novo_saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        embed.add_field(name="💳 Novo Saldo", value=f"{novo_saldo:,} Hunos", inline=False)
        
        await ctx.send(embed=embed)

    @cassino.command(name="dado")
    async def cassino_dado(self, ctx, aposta: int):
        """Joga dados (1-6)
        Uso: !cassino dado <valor>
        """
        if aposta < 1:
            await ctx.send("❌ Aposta mínima: 1 Huno.")
            return
        
        saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        
        if saldo < aposta:
            await ctx.send(f"❌ Saldo insuficiente! Você tem {saldo:,} Hunos.")
            return
        
        # Rola 2 dados
        dado1 = random.randint(1, 6)
        dado2 = random.randint(1, 6)
        total = dado1 + dado2
        
        # Multiplicador baseado no total
        if total == 12:
            multiplicador = 6
            mensagem = "🎉 **DOIS SEIS!** JACKPOT!"
        elif total == 2:
            multiplicador = 6
            mensagem = "🎉 **DOIS UM!** JACKPOT!"
        elif total >= 10:
            multiplicador = 3
            mensagem = f"🎉 **{total}**! Alta!"
        elif total <= 4:
            multiplicador = 3
            mensagem = f"🎉 **{total}**! Baixa!"
        else:
            multiplicador = 1
            mensagem = f"😐 **{total}** - Normal"
        
        ganho = aposta * multiplicador
        
        # Atualiza o saldo
        if ganho > 0:
            db_hunos.add_hunos(str(ctx.author.id), str(ctx.guild.id), ganho)
        else:
            db_hunos.remove_hunos(str(ctx.author.id), str(ctx.guild.id), aposta)
        
        embed = discord.Embed(
            title="🎲 Dados",
            description=mensagem,
            color=discord.Color.green() if ganho > 0 else discord.Color.red()
        )
        embed.add_field(name="🎲 Dado 1", value=dado1, inline=True)
        embed.add_field(name="🎲 Dado 2", value=dado2, inline=True)
        embed.add_field(name="📊 Total", value=total, inline=True)
        embed.add_field(name="💰 Aposta", value=f"{aposta:,} Hunos", inline=True)
        
        if ganho > 0:
            embed.add_field(name="🎉 Ganho", value=f"+{ganho:,} Hunos", inline=True)
        else:
            embed.add_field(name="💸 Perda", value=f"{aposta:,} Hunos", inline=True)
        
        novo_saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        embed.add_field(name="💳 Novo Saldo", value=f"{novo_saldo:,} Hunos", inline=False)
        
        await ctx.send(embed=embed)

    @cassino.command(name="caraoucoroa", aliases=["coc"])
    async def cassino_coc(self, ctx, aposta: int, escolha: str = None):
        """Cara ou Coroa
        Uso: !cassino caraoucoroa <valor> [cara/coroa]
        """
        if aposta < 1:
            await ctx.send("❌ Aposta mínima: 1 Huno.")
            return
        
        saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        
        if saldo < aposta:
            await ctx.send(f"❌ Saldo insuficiente! Você tem {saldo:,} Hunos.")
            return
        
        # Escolha aleatória
        resultado = random.choice(["cara", "coroa"])
        
        if escolha:
            escolha = escolha.lower()
            if escolha not in ["cara", "coroa"]:
                await ctx.send("❌ Escolha 'cara' ou 'coroa'.")
                return
            
            if escolha == resultado:
                ganho = aposta * 2
                cor = discord.Color.green()
                mensagem = f"🎉 **{resultado.upper()}!** Você acertou!"
            else:
                ganho = 0
                cor = discord.Color.red()
                mensagem = f"❌ **{resultado.upper()}!** Você errou."
        else:
            # Se não escolheu, ganha 2x se acertar
            escolha_auto = random.choice(["cara", "coroa"])
            if escolha_auto == resultado:
                ganho = aposta * 2
                cor = discord.Color.green()
                mensagem = f"🎉 **{resultado.upper()}!** Você ganhou!"
            else:
                ganho = 0
                cor = discord.Color.red()
                mensagem = f"❌ **{resultado.upper()}!** Você perdeu."
        
        # Atualiza o saldo
        if ganho > 0:
            db_hunos.add_hunos(str(ctx.author.id), str(ctx.guild.id), ganho)
        else:
            db_hunos.remove_hunos(str(ctx.author.id), str(ctx.guild.id), aposta)
        
        embed = discord.Embed(
            title="🪙 Cara ou Coroa",
            description=mensagem,
            color=cor
        )
        embed.add_field(name="🪙 Resultado", value=resultado.upper(), inline=True)
        embed.add_field(name="💰 Aposta", value=f"{aposta:,} Hunos", inline=True)
        
        if ganho > 0:
            embed.add_field(name="🎉 Ganho", value=f"+{ganho:,} Hunos", inline=True)
        else:
            embed.add_field(name="💸 Perda", value=f"{aposta:,} Hunos", inline=True)
        
        novo_saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        embed.add_field(name="💳 Novo Saldo", value=f"{novo_saldo:,} Hunos", inline=False)
        
        await ctx.send(embed=embed)

    @cassino.command(name="blackjack", aliases=["bj"])
    async def cassino_blackjack(self, ctx, aposta: int):
        """Joga Blackjack (21)
        Uso: !cassino blackjack <valor>
        """
        if aposta < 1:
            await ctx.send("❌ Aposta mínima: 1 Huno.")
            return
        
        saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        
        if saldo < aposta:
            await ctx.send(f"❌ Saldo insuficiente! Você tem {saldo:,} Hunos.")
            return
        
        # Função para puxar carta
        def puxar_carta():
            return random.randint(1, 11)
        
        # Mão do jogador
        mao_jogador = [puxar_carta(), puxar_carta()]
        mao_bot = [puxar_carta(), puxar_carta()]
        
        # Mostra as cartas
        texto = f"🃏 Suas cartas: **{mao_jogador}** = {sum(mao_jogador)}\n"
        texto += f"🃏 Cartas do dealer: **{mao_bot[0]}** + ❓"
        
        embed = discord.Embed(
            title="🎴 Blackjack",
            description=texto,
            color=discord.Color.blue()
        )
        embed.add_field(name="💰 Aposta", value=f"{aposta:,} Hunos", inline=True)
        
        await ctx.send(embed=embed)
        
        # Loop do jogador
        while sum(mao_jogador) < 21:
            await ctx.send("Deseja **comprar** mais uma carta ou **parar**?")
            
            def check(msg):
                return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.lower() in ["comprar", "parar"]
            
            try:
                resposta = await self.bot.wait_for('message', timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await ctx.send("⏰ Tempo esgotado! Você parou.")
                break
            
            if resposta.content.lower() == "comprar":
                nova_carta = puxar_carta()
                mao_jogador.append(nova_carta)
                
                texto = f"🃏 Suas cartas: **{mao_jogador}** = {sum(mao_jogador)}\n"
                texto += f"🃏 Cartas do dealer: **{mao_bot[0]}** + ❓"
                
                embed = discord.Embed(
                    title="🎴 Blackjack",
                    description=texto,
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
                
                if sum(mao_jogador) > 21:
                    await ctx.send("💥 **Estourou!** Você passou de 21.")
                    break
            else:
                await ctx.send("✋ Você parou.")
                break
        
        # Dealer joga
        while sum(mao_bot) < 17:
            mao_bot.append(puxar_carta())
        
        # Resultado
        soma_jogador = sum(mao_jogador)
        soma_bot = sum(mao_bot)
        
        if soma_jogador > 21:
            ganho = 0
            cor = discord.Color.red()
            resultado_texto = "💥 Você estourou! Dealer venceu."
        elif soma_bot > 21:
            ganho = aposta * 2
            cor = discord.Color.green()
            resultado_texto = "🎉 Dealer estourou! Você venceu!"
        elif soma_jogador > soma_bot:
            ganho = aposta * 2
            cor = discord.Color.green()
            resultado_texto = "🎉 Você venceu!"
        elif soma_jogador < soma_bot:
            ganho = 0
            cor = discord.Color.red()
            resultado_texto = "❌ Dealer venceu!"
        else:
            ganho = aposta
            cor = discord.Color.blue()
            resultado_texto = "🤝 Empate! Sua aposta foi devolvida."
        
        # Mostra resultado final
        texto_final = f"🃏 Suas cartas: **{mao_jogador}** = {soma_jogador}\n"
        texto_final += f"🃏 Cartas do dealer: **{mao_bot}** = {soma_bot}"
        
        embed = discord.Embed(
            title="🎴 Blackjack - Resultado",
            description=f"{resultado_texto}\n\n{texto_final}",
            color=cor
        )
        embed.add_field(name="💰 Aposta", value=f"{aposta:,} Hunos", inline=True)
        
        if ganho > 0:
            db_hunos.add_hunos(str(ctx.author.id), str(ctx.guild.id), ganho)
            embed.add_field(name="🎉 Ganho", value=f"+{ganho:,} Hunos", inline=True)
        elif ganho == 0:
            db_hunos.remove_hunos(str(ctx.author.id), str(ctx.guild.id), aposta)
            embed.add_field(name="💸 Perda", value=f"{aposta:,} Hunos", inline=True)
        else:
            embed.add_field(name="🤝 Empate", value="Sua aposta foi devolvida", inline=True)
        
        novo_saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        embed.add_field(name="💳 Novo Saldo", value=f"{novo_saldo:,} Hunos", inline=False)
        
        await ctx.send(embed=embed)

    @cassino.command(name="caca-niquel", aliases=["caçaniquel", "slot"])
    async def cassino_slot(self, ctx, aposta: int):
        """Joga no caça-níquel
        Uso: !cassino caca-niquel <valor>
        """
        if aposta < 1:
            await ctx.send("❌ Aposta mínima: 1 Huno.")
            return
        
        saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        
        if saldo < aposta:
            await ctx.send(f"❌ Saldo insuficiente! Você tem {saldo:,} Hunos.")
            return
        
        # Símbolos do caça-níquel
        simbolos = ["🍒", "🍋", "🍊", "⭐", "💎", "🎰"]
        
        # Roda os 3 slots
        slot1 = random.choice(simbolos)
        slot2 = random.choice(simbolos)
        slot3 = random.choice(simbolos)
        
        # Verifica combinações
        if slot1 == slot2 == slot3:
            if slot1 == "🎰":
                multiplicador = 10
                mensagem = "🎰🎰🎰 **JACKPOT!** 10x!"
            elif slot1 == "💎":
                multiplicador = 5
                mensagem = "💎💎💎 **5x!**"
            elif slot1 == "⭐":
                multiplicador = 3
                mensagem = "⭐⭐⭐ **3x!**"
            elif slot1 in ["🍒", "🍋", "🍊"]:
                multiplicador = 2
                mensagem = f"{slot1}{slot1}{slot1} **2x!**"
            else:
                multiplicador = 1
                mensagem = f"{slot1}{slot2}{slot3} - Empate"
        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            multiplicador = 1
            mensagem = f"{slot1}{slot2}{slot3} - Dois iguais! Empate."
        else:
            multiplicador = 0
            mensagem = f"{slot1}{slot2}{slot3} - Nada! Perdeu."
        
        ganho = aposta * multiplicador
        
        # Atualiza o saldo
        if ganho > 0:
            db_hunos.add_hunos(str(ctx.author.id), str(ctx.guild.id), ganho)
        else:
            db_hunos.remove_hunos(str(ctx.author.id), str(ctx.guild.id), aposta)
        
        embed = discord.Embed(
            title="🎰 Caça-níquel",
            description=f"| {slot1} | {slot2} | {slot3} |\n\n{mensagem}",
            color=discord.Color.green() if ganho > 0 else discord.Color.red()
        )
        embed.add_field(name="💰 Aposta", value=f"{aposta:,} Hunos", inline=True)
        
        if ganho > 0:
            embed.add_field(name="🎉 Ganho", value=f"+{ganho:,} Hunos", inline=True)
        else:
            embed.add_field(name="💸 Perda", value=f"{aposta:,} Hunos", inline=True)
        
        novo_saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        embed.add_field(name="💳 Novo Saldo", value=f"{novo_saldo:,} Hunos", inline=False)
        
        await ctx.send(embed=embed)

    @cassino.command(name="ppt")
    async def cassino_ppt(self, ctx, aposta: int, escolha: str = None):
        """Pedra, Papel, Tesoura
        Uso: !cassino ppt <valor> [pedra/papel/tesoura]
        """
        if aposta < 1:
            await ctx.send("❌ Aposta mínima: 1 Huno.")
            return
        
        saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        
        if saldo < aposta:
            await ctx.send(f"❌ Saldo insuficiente! Você tem {saldo:,} Hunos.")
            return
        
        opcoes = ["pedra", "papel", "tesoura"]
        emojis = {"pedra": "🪨", "papel": "📄", "tesoura": "✂️"}
        
        if escolha:
            escolha = escolha.lower()
            if escolha not in opcoes:
                await ctx.send("❌ Escolha 'pedra', 'papel' ou 'tesoura'.")
                return
        else:
            escolha = random.choice(opcoes)
        
        bot_escolha = random.choice(opcoes)
        
        # Determina o vencedor
        if escolha == bot_escolha:
            ganho = aposta  # Empate, devolve a aposta
            cor = discord.Color.blue()
            resultado_texto = "🤝 Empate!"
        elif (escolha == "pedra" and bot_escolha == "tesoura") or \
             (escolha == "papel" and bot_escolha == "pedra") or \
             (escolha == "tesoura" and bot_escolha == "papel"):
            ganho = aposta * 2
            cor = discord.Color.green()
            resultado_texto = "🎉 Você venceu!"
        else:
            ganho = 0
            cor = discord.Color.red()
            resultado_texto = "❌ Você perdeu!"
        
        # Atualiza o saldo
        if ganho > 0:
            db_hunos.add_hunos(str(ctx.author.id), str(ctx.guild.id), ganho)
        else:
            db_hunos.remove_hunos(str(ctx.author.id), str(ctx.guild.id), aposta)
        
        embed = discord.Embed(
            title="🪨📄✂️ Pedra, Papel, Tesoura",
            description=f"{resultado_texto}\n\nVocê: {emojis[escolha]} {escolha.capitalize()}\nBot: {emojis[bot_escolha]} {bot_escolha.capitalize()}",
            color=cor
        )
        embed.add_field(name="💰 Aposta", value=f"{aposta:,} Hunos", inline=True)
        
        if ganho > 0:
            embed.add_field(name="🎉 Ganho", value=f"+{ganho:,} Hunos", inline=True)
        else:
            embed.add_field(name="💸 Perda", value=f"{aposta:,} Hunos", inline=True)
        
        novo_saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        embed.add_field(name="💳 Novo Saldo", value=f"{novo_saldo:,} Hunos", inline=False)
        
        await ctx.send(embed=embed)

    @cassino.command(name="corrida")
    async def cassino_corrida(self, ctx, aposta: int):
        """Corrida de dados
        Uso: !cassino corrida <valor>
        """
        if aposta < 1:
            await ctx.send("❌ Aposta mínima: 1 Huno.")
            return
        
        saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        
        if saldo < aposta:
            await ctx.send(f"❌ Saldo insuficiente! Você tem {saldo:,} Hunos.")
            return
        
        # Rola os dados
        dado_jogador = random.randint(1, 6)
        dado_bot = random.randint(1, 6)
        
        # Determina o vencedor
        if dado_jogador > dado_bot:
            ganho = aposta * 2
            cor = discord.Color.green()
            resultado_texto = "🎉 Você venceu a corrida!"
        elif dado_jogador < dado_bot:
            ganho = 0
            cor = discord.Color.red()
            resultado_texto = "❌ Você perdeu a corrida!"
        else:
            ganho = aposta
            cor = discord.Color.blue()
            resultado_texto = "🤝 Empate!"
        
        # Atualiza o saldo
        if ganho > 0:
            db_hunos.add_hunos(str(ctx.author.id), str(ctx.guild.id), ganho)
        else:
            db_hunos.remove_hunos(str(ctx.author.id), str(ctx.guild.id), aposta)
        
        # Cria barra visual
        def criar_barra(valor, tamanho=10):
            return "🏃" + "█" * valor + "░" * (tamanho - valor)
        
        embed = discord.Embed(
            title="🏁 Corrida de Dados",
            description=f"{resultado_texto}",
            color=cor
        )
        embed.add_field(
            name=f"🎲 Você ({dado_jogador})",
            value=criar_barra(dado_jogador),
            inline=False
        )
        embed.add_field(
            name=f"🤖 Bot ({dado_bot})",
            value=criar_barra(dado_bot),
            inline=False
        )
        embed.add_field(name="💰 Aposta", value=f"{aposta:,} Hunos", inline=True)
        
        if ganho > 0:
            embed.add_field(name="🎉 Ganho", value=f"+{ganho:,} Hunos", inline=True)
        else:
            embed.add_field(name="💸 Perda", value=f"{aposta:,} Hunos", inline=True)
        
        novo_saldo = db_hunos.get_hunos(str(ctx.author.id), str(ctx.guild.id))
        embed.add_field(name="💳 Novo Saldo", value=f"{novo_saldo:,} Hunos", inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Cassino(bot))