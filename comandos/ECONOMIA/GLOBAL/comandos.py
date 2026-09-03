import discord
from discord.ext import commands, tasks
from database.python.mongodb import db
from .motor import MotorEconomiaGlobal
from .producao import MotorProducao
from .governo import MotorGoverno
from .populacao import MotorPopulacao
from .comercio import MotorComercioInternacional
from .eventos import MotorEventosEconomicos


class EconomiaGlobal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.motor = MotorEconomiaGlobal(db)
        self.producao = MotorProducao(db, self.motor)
        self.governo = MotorGoverno(db, self.motor)
        self.populacao = MotorPopulacao(db, self.motor)
        self.comercio = MotorComercioInternacional(db, self.motor, self.governo)
        self.eventos = MotorEventosEconomicos(db, self.motor)
        self.ciclo_economico.start()

    def cog_unload(self):
        self.ciclo_economico.cancel()

    @tasks.loop(minutes=1)
    async def ciclo_economico(self):
        resultado = self.motor.ciclo_economico()
        estado = resultado.get("estado", {})
        print(f"🌐 Ciclo econômico: índice={estado.get('indice_precos', 0):.4f} | reposição={resultado.get('reposicoes', 0)} | empresas={resultado.get('empresas', 0)} | inadimplentes={resultado.get('inadimplentes', 0)} | populações={resultado.get('populacoes', 0)} | eventos={resultado.get('eventos', 0)}")

    @ciclo_economico.before_loop
    async def antes_ciclo(self):
        await self.bot.wait_until_ready()

    @commands.command(name="criar_evento_economico", aliases=["evento_economico"])
    @commands.has_permissions(administrator=True)
    async def criar_evento_economico(self, ctx, tipo: str, intensidade: float, duracao: int = 60):
        resultado = self.eventos.criar_evento(ctx.guild.id, tipo, intensidade / 100, duracao)
        if "erro" in resultado:
            tipos = ", ".join(self.eventos.TIPOS.keys())
            await ctx.send(f"❌ Evento inválido. Tipos disponíveis: `{tipos}`")
            return
        embed = discord.Embed(title="📉 Evento econômico iniciado", color=discord.Color.orange())
        embed.add_field(name="Tipo", value=resultado["tipo"].replace("_", " ").title())
        embed.add_field(name="Intensidade", value=f"{resultado['intensidade'] * 100:.2f}%")
        embed.add_field(name="Duração", value=f"{resultado['duracao_ciclos']} ciclos")
        embed.add_field(name="Efeito", value=resultado["descricao"], inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="eventos_economicos", aliases=["eventos"])
    async def eventos_economicos(self, ctx):
        eventos = self.eventos.eventos_ativos(ctx.guild.id)
        if not eventos:
            await ctx.send("📊 Não existem eventos econômicos ativos neste governo.")
            return
        embed = discord.Embed(title="⚠️ Eventos Econômicos Ativos", color=discord.Color.orange())
        for evento in eventos[:20]:
            embed.add_field(
                name=evento["tipo"].replace("_", " ").title(),
                value=f"Intensidade: **{evento['intensidade'] * 100:.2f}%**\nCiclos restantes: **{evento['ciclos_restantes']}**",
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(name="configurar_rota")
    @commands.has_permissions(administrator=True)
    async def configurar_rota(self, ctx, destino_id: str, modelo: str = "tradicional", distancia: float = 1.0):
        resultado = self.comercio.configurar_rota(ctx.guild.id, destino_id, distancia, modelo)
        if "erro" in resultado:
            await ctx.send(f"❌ {resultado['erro']}")
            return
        embed = discord.Embed(title="🛤️ Rota comercial configurada", color=discord.Color.green())
        embed.add_field(name="Origem", value=str(ctx.guild.id))
        embed.add_field(name="Destino", value=str(destino_id))
        embed.add_field(name="Modelo", value=resultado["modelo"].capitalize())
        embed.add_field(name="Custo logístico", value=f"{resultado['custo_logistico_percentual'] * 100:.2f}%")
        await ctx.send(embed=embed)

    @commands.command(name="comerciar")
    @commands.has_permissions(administrator=True)
    async def comerciar(self, ctx, destino_id: str, produto: str, valor_bronze: float, quantidade: int = 1):
        resultado = self.comercio.realizar_comercio(ctx.guild.id, destino_id, produto, valor_bronze, quantidade)
        if "erro" in resultado:
            mensagens = {"rota_inexistente": "Não existe uma rota comercial ativa para esse destino.", "governo_inexistente": "Os dois governos precisam estar configurados.", "comercio_interno": "Utilize mercados locais para comércio interno."}
            await ctx.send(f"❌ {mensagens.get(resultado['erro'], resultado['erro'])}")
            return
        embed = discord.Embed(title="🚢 Comércio internacional realizado", color=discord.Color.blue())
        embed.add_field(name="Produto", value=resultado["produto"])
        embed.add_field(name="Quantidade", value=str(resultado["quantidade"]))
        embed.add_field(name="Valor da carga", value=self.motor.formatar_moeda(resultado["valor_carga_bronze"]))
        embed.add_field(name="Logística", value=self.motor.formatar_moeda(resultado["custo_logistico_bronze"]))
        embed.add_field(name="Tarifa de exportação", value=self.motor.formatar_moeda(resultado["tarifa_exportacao_bronze"]))
        embed.add_field(name="Tarifa de importação", value=self.motor.formatar_moeda(resultado["tarifa_importacao_bronze"]))
        embed.add_field(name="Custo final", value=self.motor.formatar_moeda(resultado["custo_final_bronze"]), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="balanca_comercial", aliases=["balanca"])
    async def balanca_comercial(self, ctx):
        dados = self.comercio.balanca_comercial(ctx.guild.id)
        saldo = float(dados.get("saldo_bronze", 0))
        cor = discord.Color.green() if saldo >= 0 else discord.Color.red()
        embed = discord.Embed(title="⚖️ Balança Comercial", color=cor)
        embed.add_field(name="Exportações", value=self.motor.formatar_moeda(dados.get("exportacoes_bronze", 0)))
        embed.add_field(name="Importações", value=self.motor.formatar_moeda(dados.get("importacoes_bronze", 0)))
        embed.add_field(name="Saldo", value=self.motor.formatar_moeda(abs(saldo)) + (" de superávit" if saldo >= 0 else " de déficit"), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="configurar_mercado", aliases=["configmercado"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def configurar_mercado(self, ctx, tipo: str, categoria: str = "comum"):
        try:
            self.motor.configurar_mercado(ctx.guild.id, ctx.channel.id, tipo.lower(), categoria.lower())
        except ValueError as erro:
            await ctx.send(embed=discord.Embed(title="❌ Configuração inválida", description=str(erro), color=discord.Color.red()))
            return
        await ctx.send(embed=discord.Embed(title="🏪 Mercado configurado", description=f"Canal: {ctx.channel.mention}\nTipo: **{tipo.capitalize()} ({categoria})**", color=discord.Color.green()))

    @commands.command(name="repor_estoque")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def repor_estoque(self, ctx, produto_id: str, quantidade: int = None):
        resultado = self.producao.repor_mercado(ctx.guild.id, ctx.channel.id, produto_id, quantidade)
        if "erro" in resultado:
            await ctx.send(f"❌ Reposição não realizada: `{resultado['erro']}`")
            return
        custo = resultado["custo"]
        embed = discord.Embed(title="🏭 Estoque produzido", color=discord.Color.green())
        embed.add_field(name="Quantidade", value=str(resultado["quantidade"]), inline=True)
        embed.add_field(name="Custo total", value=self.motor.formatar_moeda(custo["total"]), inline=True)
        embed.add_field(name="Salários", value=self.motor.formatar_moeda(custo["salarios"]), inline=True)
        embed.add_field(name="Insumos", value=self.motor.formatar_moeda(custo["insumos"]), inline=True)
        embed.add_field(name="Energia", value=self.motor.formatar_moeda(custo["energia"]), inline=True)
        embed.add_field(name="Logística", value=self.motor.formatar_moeda(custo["logistica"]), inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="criar_governo")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def criar_governo(self, ctx, nome: str, tesouro_bronze: float = 0):
        resultado = self.governo.criar_governo(ctx.guild.id, nome, tesouro_bronze)
        await ctx.send(embed=discord.Embed(title="🏛️ Governo criado", description=f"**{resultado['nome']}**\nTesouro inicial: {self.motor.formatar_moeda(tesouro_bronze)}", color=discord.Color.green()))

    @commands.command(name="configurar_populacao", aliases=["configpopulacao"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def configurar_populacao(self, ctx, quantidade: int):
        resultado = self.populacao.configurar_populacao(ctx.guild.id, quantidade)
        if "erro" in resultado:
            await ctx.send(f"❌ {resultado['erro']}")
            return
        classes = resultado["classes"]
        embed = discord.Embed(title="👥 População configurada", color=discord.Color.green())
        embed.add_field(name="População total", value=f"{resultado['quantidade']:,}")
        embed.add_field(name="Classe baixa", value=f"{classes.get('baixa', 0):,}")
        embed.add_field(name="Classe média", value=f"{classes.get('media', 0):,}")
        embed.add_field(name="Classe alta", value=f"{classes.get('alta', 0):,}")
        embed.add_field(name="Renda mensal agregada", value=self.motor.formatar_moeda(resultado["renda_mensal_total_bronze"]), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="definir_desemprego")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def definir_desemprego(self, ctx, percentual: float):
        resultado = self.populacao.definir_desemprego(ctx.guild.id, percentual / 100)
        if "erro" in resultado:
            await ctx.send("❌ Configure a população antes.")
            return
        embed = discord.Embed(title="📉 Mercado de trabalho atualizado", color=discord.Color.orange())
        embed.add_field(name="Desemprego", value=f"{resultado['taxa'] * 100:.2f}%")
        embed.add_field(name="Empregados", value=f"{resultado['empregados']:,}")
        embed.add_field(name="Desempregados", value=f"{resultado['desempregados']:,}")
        await ctx.send(embed=embed)

    @commands.command(name="populacao", aliases=["demografia"])
    @commands.guild_only()
    async def populacao(self, ctx):
        pop = self.populacao.populacoes.find_one({"governo_id": str(ctx.guild.id)})
        if not pop:
            await ctx.send("❌ A população econômica ainda não foi configurada.")
            return
        poder = self.populacao.poder_de_compra(ctx.guild.id)
        embed = discord.Embed(title="👥 Economia da População", color=discord.Color.blue())
        embed.add_field(name="População", value=f"{pop.get('quantidade', 0):,}")
        embed.add_field(name="Empregados", value=f"{pop.get('empregados', 0):,}")
        embed.add_field(name="Desemprego", value=f"{float(pop.get('taxa_desemprego', 0)) * 100:.2f}%")
        embed.add_field(name="Renda nominal", value=self.motor.formatar_moeda(poder.get("renda_nominal", 0)), inline=False)
        embed.add_field(name="Poder de compra real", value=self.motor.formatar_moeda(poder.get("renda_real", 0)), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="definir_imposto")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def definir_imposto(self, ctx, tipo: str, percentual: float):
        resultado = self.governo.definir_imposto(ctx.guild.id, tipo, percentual / 100)
        if "erro" in resultado:
            await ctx.send("❌ Tipo de imposto inválido. Use: venda, renda, empresa, importacao, exportacao ou propriedade.")
            return
        await ctx.send(embed=discord.Embed(title="📜 Imposto atualizado", description=f"**{tipo.capitalize()}**: {percentual:.2f}%", color=discord.Color.gold()))

    @commands.command(name="definir_tarifa")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def definir_tarifa(self, ctx, tipo: str, percentual: float):
        resultado = self.governo.definir_tarifa(ctx.guild.id, tipo, percentual / 100)
        if "erro" in resultado:
            await ctx.send("❌ Tipo inválido. Use: importacao ou exportacao.")
            return
        await ctx.send(embed=discord.Embed(title="🚢 Tarifa comercial atualizada", description=f"**{tipo.capitalize()}**: {percentual:.2f}%", color=discord.Color.gold()))

    @commands.command(name="tesouro")
    @commands.guild_only()
    async def tesouro(self, ctx):
        dados = self.governo.relatorio(ctx.guild.id)
        if "erro" in dados:
            await ctx.send("❌ Este servidor ainda não possui um governo econômico configurado.")
            return
        governo = dados["governo"]; tesouro = dados["tesouro"]
        embed = discord.Embed(title=f"🏛️ Tesouro — {governo['nome']}", color=discord.Color.gold())
        embed.add_field(name="Saldo", value=self.motor.formatar_moeda(tesouro.get("saldo_bronze", 0)), inline=False)
        embed.add_field(name="Receita acumulada", value=self.motor.formatar_moeda(tesouro.get("receita_total_bronze", 0)))
        embed.add_field(name="Gasto acumulado", value=self.motor.formatar_moeda(tesouro.get("gasto_total_bronze", 0)))
        taxas = governo.get("taxas", {})
        texto = "\n".join(f"{nome}: {valor * 100:.2f}%" for nome, valor in taxas.items()) or "Nenhuma"
        embed.add_field(name="Impostos", value=texto, inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="mercado")
    @commands.guild_only()
    async def mercado(self, ctx):
        mercado = self.motor.mercado_do_canal(ctx.guild.id, ctx.channel.id)
        if not mercado:
            await ctx.send("❌ Este canal ainda não é um mercado configurado.")
            return
        receitas = float(mercado.get("receita_bronze", 0)); custos = float(mercado.get("custos_operacionais_bronze", 0))
        embed = discord.Embed(title="📊 Mercado Local", color=discord.Color.gold())
        embed.add_field(name="Tipo", value=f"{mercado['tipo'].capitalize()} — {mercado.get('categoria', 'comum')}")
        embed.add_field(name="Demanda", value=str(round(mercado.get("demanda", 0), 2)))
        embed.add_field(name="Oferta", value=str(round(mercado.get("oferta", 0), 2)))
        embed.add_field(name="Receitas", value=self.motor.formatar_moeda(receitas))
        embed.add_field(name="Custos", value=self.motor.formatar_moeda(custos))
        embed.add_field(name="Resultado", value=self.motor.formatar_moeda(receitas - custos))
        await ctx.send(embed=embed)

    @commands.command(name="economia_global", aliases=["eco_global", "macroeconomia"])
    async def economia_global(self, ctx):
        dados = self.motor.relatorio_global()
        embed = discord.Embed(title="🌐 Economia Global de Tensura", color=discord.Color.blue())
        embed.add_field(name="Índice de preços", value=f"{float(dados.get('indice_precos', 100.0)):.4f}")
        embed.add_field(name="Inflação por minuto", value=f"{float(dados.get('inflacao_minuto', 0.0)) * 100:+.4f}%")
        embed.add_field(name="Liquidez internacional", value=f"{dados.get('liquidez_ouro', 0):,.2f} ouro")
        embed.add_field(name="Fluxo de capitais", value=self.motor.formatar_moeda(dados.get('fluxo_capital', 0)), inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(EconomiaGlobal(bot))
