import discord
from discord.ext import commands
from database.python.mongodb import db
import json
import os

# Ordem de exibição das raridades no embed
ORDEM_RARIDADES = ["Comum", "Única", "Raça", "Definitiva", "Suprema", "Extra"]

# Mapeamento de raridade para arquivo JSON
ARQUIVOS_HABILIDADES = {
    "Comum": "database/json/habilidades/habs_comuns.json",
    "Única": "database/json/habilidades/habs_unicas.json",
    "Raça": "database/json/habilidades/habs_raca.json",
    "Definitiva": "database/json/habilidades/habs_definitivas.json",
    "Suprema": "database/json/habilidades/habs_supremas.json",
    "Extra": "database/json/habilidades/habs_extras.json"
}

# Mapeamento de raridade em minúsculo para o nome correto
RARIDADE_MAP = {
    "comum": "Comum",
    "única": "Única",
    "unica": "Única",
    "raça": "Raça",
    "raca": "Raça",
    "definitiva": "Definitiva",
    "suprema": "Suprema",
    "extra": "Extra"
}

# Cor por raridade
COR_RARIDADE = {
    "Comum": 0x95a5a6,
    "Única": 0x3498db,
    "Raça": 0x2ecc71,
    "Definitiva": 0x9b59b6,
    "Suprema": 0xe67e22,
    "Extra": 0xe74c3c,
}

class Habilidades(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache_habilidades = self._carregar_habilidades()
        print(f"✅ Total no cache: {len(self.cache_habilidades)} habilidades")

    def _carregar_habilidades(self):
        """Carrega todas as habilidades dos arquivos JSON"""
        habilidades_cache = {}
        
        for raridade, arquivo in ARQUIVOS_HABILIDADES.items():
            try:
                if not os.path.exists(arquivo):
                    print(f"❌ Arquivo não existe: {arquivo}")
                    continue
                    
                print(f"📂 Lendo: {arquivo}")
                with open(arquivo, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    print(f"  ✅ {len(dados)} habilidades encontradas em {raridade}")
                    
                    for hab in dados:
                        hab_id = str(hab.get("ID", "")).strip()
                        if hab_id:
                            raridade_raw = hab.get("raridade", "").lower()
                            raridade_corrigida = RARIDADE_MAP.get(raridade_raw, raridade)
                            
                            habilidades_cache[hab_id] = {
                                "id": hab_id,
                                "nome": hab.get("nome", "Desconhecido"),
                                "raridade": raridade_corrigida,
                                "descricao": hab.get("descricao", ""),
                                "tipo": hab.get("tipo", ""),
                                "elemento": hab.get("elemento", None),
                                "passiva": hab.get("passiva", "nao"),
                                "ativa": hab.get("ativa", "nao"),
                                "bonus": hab.get("bonus", {}),
                                "hab_ativa": hab.get("hab_ativa", "")
                            }
                        else:
                            print(f"  ⚠️ Habilidade sem ID: {hab}")
                            
            except FileNotFoundError:
                print(f"❌ Arquivo não encontrado: {arquivo}")
            except json.JSONDecodeError as e:
                print(f"❌ Erro ao ler JSON {arquivo}: {e}")
            except Exception as e:
                print(f"❌ Erro inesperado em {arquivo}: {e}")
                
        return habilidades_cache

    def _buscar_habilidade(self, hab_id: str):
        """Busca uma habilidade pelo ID no cache"""
        hab_id = hab_id.strip().strip('"').strip("'")
        return self.cache_habilidades.get(hab_id)

    def _parse_habilidades(self, habilidades_raw):
        """Converte qualquer formato de habilidades para lista de IDs"""
        if not habilidades_raw:
            return []
        
        if isinstance(habilidades_raw, list):
            ids = []
            for item in habilidades_raw:
                if isinstance(item, str):
                    if ',' in item:
                        ids.extend([i.strip().strip('"').strip("'") for i in item.split(',') if i.strip()])
                    else:
                        ids.append(item.strip().strip('"').strip("'"))
                else:
                    ids.append(str(item).strip().strip('"').strip("'"))
            return [id for id in ids if id]
        
        if isinstance(habilidades_raw, str):
            limpa = habilidades_raw.replace('[', '').replace(']', '').replace('"', '').replace("'", '')
            return [id.strip() for id in limpa.split(',') if id.strip()]
        
        return []

    @commands.command(name="habilidades", aliases=["habs", "habils", "skills"])
    async def habs(self, ctx: commands.Context):
        if db is None:
            await ctx.send("❌ Banco de dados não conectado.")
            return
        
        # ===== CORREÇÃO AQUI: Busca na coleção Habilidades =====
        habilidades_collection = db["Habilidades"]

        # Busca o documento de habilidades do jogador
        doc_habilidades = habilidades_collection.find_one({
            "ID": str(ctx.author.id),
            "guild_id": str(ctx.guild.id)
        })

        if not doc_habilidades:
            await ctx.send("❌ Você não possui habilidades registradas.")
            return

        if not doc_habilidades.get("habilidades"):
            await ctx.send("❌ Você ainda não possui nenhuma habilidade.")
            return

        ids_do_jogador = self._parse_habilidades(doc_habilidades["habilidades"])

        if not ids_do_jogador:
            await ctx.send("❌ Você ainda não possui nenhuma habilidade.")
            return

        habilidades_encontradas = []
        ids_nao_encontrados = []
        
        for hab_id in ids_do_jogador:
            hab = self._buscar_habilidade(hab_id)
            if hab:
                habilidades_encontradas.append(hab)
            else:
                ids_nao_encontrados.append(hab_id)

        if not habilidades_encontradas:
            await ctx.send(f"❌ Nenhuma habilidade encontrada no catálogo. IDs: {', '.join(ids_nao_encontrados[:5])}")
            return

        agrupado = {}
        for hab in habilidades_encontradas:
            raridade = hab.get("raridade", "Outras")
            agrupado.setdefault(raridade, []).append(hab)

        embed = discord.Embed(
            title=f"📖 Catálogo de Habilidades — {ctx.author.display_name}",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        raridades_presentes = list(agrupado.keys())
        ordem_final = [r for r in ORDEM_RARIDADES if r in agrupado] + \
                      [r for r in raridades_presentes if r not in ORDEM_RARIDADES]

        for raridade in ordem_final:
            lista = agrupado[raridade]
            texto = "\n".join(f"`{h['id']}` **{h['nome']}**" for h in lista)
            
            if len(texto) > 1024:
                texto = texto[:1000] + "\n... (lista truncada)"
                
            embed.add_field(
                name=f"{raridade} ({len(lista)})",
                value=texto,
                inline=False
            )

        if ids_nao_encontrados:
            embed.add_field(
                name="⚠️ IDs não encontrados",
                value=f"{', '.join(ids_nao_encontrados[:10])}" + ("..." if len(ids_nao_encontrados) > 10 else ""),
                inline=False
            )

        embed.set_footer(text=f"Total de habilidades: {len(habilidades_encontradas)}")
        await ctx.send(embed=embed)

    # ===== COMANDOS DE TESTE =====
    
    @commands.command(name="testhabilidades")
    async def testhabilidades(self, ctx):
        """Testa a coleção Habilidades no MongoDB"""
        
        if db is None:
            await ctx.send("❌ Banco não conectado.")
            return
        
        habilidades_collection = db["Habilidades"]
        
        # Busca o documento do jogador
        doc = habilidades_collection.find_one({
            "ID": str(ctx.author.id),
            "guild_id": str(ctx.guild.id)
        })
        
        if not doc:
            await ctx.send(f"❌ Documento não encontrado na coleção Habilidades.")
            return
        
        # Mostra o documento
        texto = f"**Documento na coleção Habilidades:**\n```json\n{json.dumps(doc, indent=2, default=str)[:1900]}\n```"
        await ctx.send(texto)

async def setup(bot):
    await bot.add_cog(Habilidades(bot))