import asyncio
import os

import datetime
import discord

from database.python.users import cadastro
from dotenv import load_dotenv
from discord.ext import commands
from database.python.mongodb import db
from database.python.Hunos import init_db_hunos
from comandos.ECONOMIA.auditoria import AuditoriaEconomia
from comandos.ECONOMIA.GLOBAL.ciclo_automatico import configurar_ciclo_economico
from comandos.ECONOMIA.GLOBAL.diagnostico import DiagnosticoEconomiaGlobal

init_db_hunos(db)

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)


@bot.event
async def on_member_join(member):
    cadastro(user_id=member.id, guild_id=member.guild.id)


@bot.event
async def on_ready():
    fuso_horario = datetime.timezone(datetime.timedelta(hours=-3))
    agora = datetime.datetime.now(fuso_horario)
    canal = bot.get_channel(1543040912912031775)
    print(f"Bot conectado como {bot.user}")
    if canal is not None:
        embed = discord.Embed(title="🟢 | Online", description="Moon Tensura está online e pronto para o RPG", colour=0x1caa00, timestamp=agora)
        embed.set_footer(text="Tensura Moon - Korczak Technologies!")
        await canal.send(embed=embed)
    for guild in bot.guilds:
        membros = [member for member in guild.members if not member.bot]
        quantidade = cadastro(membros)
        print(f"{guild.name}: {quantidade} usuários processados.")

    if not getattr(bot, "diagnostico_economia_executado", False):
        diagnostico = await asyncio.to_thread(DiagnosticoEconomiaGlobal(db).executar)
        bot.diagnostico_economia_executado = True
        print(f"Diagnóstico econômico: {diagnostico['ok']}/{diagnostico['total']} módulos válidos ({diagnostico['saude_percentual']}%).")
        if diagnostico["erros"]:
            for item in diagnostico["itens"]:
                if item["status"] == "erro":
                    print(f"[ECONOMIA][ERRO] {item['nome']}: {item['erro']}")

    ciclo = configurar_ciclo_economico(bot, db, intervalo_segundos=60)
    if not getattr(ciclo, "_ativo", False):
        await ciclo.iniciar()
        print("Ciclo econômico global automático iniciado: intervalo de 60 segundos.")


async def carregar_extensoes():
    extensoes = [
        "comandos.RPG.luta", "comandos.RPG.treino", "comandos.RPG.magias", "comandos.RPG.habs", "comandos.RPG.usarhab", "comandos.RPG.status", "comandos.RPG.nivel", "comandos.RPG.nascimento", "comandos.RPG.correcoes_luta", "comandos.RPG.status_habilidades",
        "comandos.ECONOMIA.cassino", "comandos.ECONOMIA.loja", "comandos.ECONOMIA.loja_canais", "comandos.ECONOMIA.Hunos", "comandos.ECONOMIA.Mora", "comandos.ECONOMIA.recompensas", "comandos.ECONOMIA.hunos_interacoes",
        "comandos.ECONOMIA.GLOBAL.comandos", "comandos.ECONOMIA.GLOBAL.banco_central", "comandos.ECONOMIA.GLOBAL.credito_comandos", "comandos.ECONOMIA.GLOBAL.comercio_comandos", "comandos.ECONOMIA.GLOBAL.trabalho_comandos",
        "comandos.ADMINISTRACAO.autorole_commands", "comandos.ADMINISTRACAO.autorole", "comandos.ADMINISTRACAO.configurações", "comandos.ADMINISTRACAO.moderacao", "comandos.ADMINISTRACAO.automod", "comandos.ADMINISTRACAO.boas_vindas", "comandos.ADMINISTRACAO.logs", "comandos.ADMINISTRACAO.ajuda"
    ]

    auditoria = await asyncio.to_thread(AuditoriaEconomia(db).executar)
    print(f"Auditoria ECONOMIA: {AuditoriaEconomia.resumo(auditoria)}")
    if auditoria["arquivos_com_erro"]:
        for item in auditoria["detalhes"]:
            if item["status"] == "erro":
                print(f"[AUDITORIA][ERRO] {item['arquivo']}: {' | '.join(item['erros'])}")
    if auditoria["conflitos_comandos"]:
        print("[AUDITORIA] Conflitos de comandos detectados:")
        for conflito in auditoria["conflitos_comandos"]:
            print(f"  - {conflito['nome']}: {', '.join(conflito['arquivos'])}")
        raise RuntimeError("A auditoria da ECONOMIA encontrou comandos duplicados. Corrija os conflitos antes de iniciar o bot.")

    for extensao in extensoes:
        await bot.load_extension(extensao)


TOKEN = os.getenv("DISCORD_TOKEN")


async def main():
    async with bot:
        await carregar_extensoes()
        await bot.start(TOKEN)


asyncio.run(main())
