import re
import time
from collections import defaultdict, deque

import discord
from discord.ext import commands

from database.python.mongodb import db


CONFIG = db["configuracoes_servidor"]


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_history = defaultdict(deque)

    def get_config(self, guild_id: int):
        return CONFIG.find_one({"guild_id": guild_id}) or {"guild_id": guild_id}

    def update_config(self, guild_id: int, data: dict):
        CONFIG.update_one(
            {"guild_id": guild_id},
            {"$set": data},
            upsert=True
        )

    def is_exempt(self, member):
        return (
            member.guild_permissions.administrator
            or member.bot
        )

    async def log(self, guild, title, description):
        config = self.get_config(guild.id)
        channel_id = config.get("log_channel_id")
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if channel is None:
            return
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass

    @commands.group(name="automod", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def automod(self, ctx):
        config = self.get_config(ctx.guild.id)
        embed = discord.Embed(
            title="🛡️ AutoMod",
            description="Sistema automático de proteção do servidor.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Status",
            value="✅ Ativado" if config.get("automod_enabled", False) else "❌ Desativado",
            inline=False
        )
        embed.add_field(
            name="Filtros",
            value=(
                f"🔗 Links: {'ON' if config.get('filter_links', False) else 'OFF'}\n"
                f"🤬 Palavras bloqueadas: {'ON' if config.get('filter_words', False) else 'OFF'}\n"
                f"📨 Anti-spam: {'ON' if config.get('anti_spam', False) else 'OFF'}"
            ),
            inline=False
        )
        embed.add_field(
            name="Comandos",
            value=(
                "`!automod toggle`\n"
                "`!automod links`\n"
                "`!automod words`\n"
                "`!automod spam`\n"
                "`!automod addword <palavra>`\n"
                "`!automod delword <palavra>`\n"
                "`!automod listwords`"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @automod.command(name="toggle")
    async def toggle(self, ctx):
        config = self.get_config(ctx.guild.id)
        enabled = not config.get("automod_enabled", False)
        self.update_config(ctx.guild.id, {"automod_enabled": enabled})
        await ctx.send(embed=discord.Embed(
            title="🛡️ AutoMod",
            description=f"Sistema {'ativado' if enabled else 'desativado'}.",
            color=discord.Color.green() if enabled else discord.Color.red()
        ))

    @automod.command(name="links")
    async def links(self, ctx):
        config = self.get_config(ctx.guild.id)
        value = not config.get("filter_links", False)
        self.update_config(ctx.guild.id, {"filter_links": value})
        await ctx.send(embed=discord.Embed(
            title="🔗 Filtro de Links",
            description=f"Filtro {'ativado' if value else 'desativado'}.",
            color=discord.Color.green() if value else discord.Color.red()
        ))

    @automod.command(name="words")
    async def words(self, ctx):
        config = self.get_config(ctx.guild.id)
        value = not config.get("filter_words", False)
        self.update_config(ctx.guild.id, {"filter_words": value})
        await ctx.send(embed=discord.Embed(
            title="🤬 Filtro de Palavras",
            description=f"Filtro {'ativado' if value else 'desativado'}.",
            color=discord.Color.green() if value else discord.Color.red()
        ))

    @automod.command(name="spam")
    async def spam(self, ctx):
        config = self.get_config(ctx.guild.id)
        value = not config.get("anti_spam", False)
        self.update_config(ctx.guild.id, {"anti_spam": value})
        await ctx.send(embed=discord.Embed(
            title="📨 Anti-Spam",
            description=f"Sistema {'ativado' if value else 'desativado'}.",
            color=discord.Color.green() if value else discord.Color.red()
        ))

    @automod.command(name="addword")
    async def addword(self, ctx, *, word: str):
        config = self.get_config(ctx.guild.id)
        words = config.get("blocked_words", [])
        word = word.lower().strip()
        if word not in words:
            words.append(word)
            self.update_config(ctx.guild.id, {"blocked_words": words})
        await ctx.send(embed=discord.Embed(
            title="✅ Palavra Adicionada",
            description=f"`{word}` foi adicionada à lista.",
            color=discord.Color.green()
        ))

    @automod.command(name="delword", aliases=["removeword"])
    async def delword(self, ctx, *, word: str):
        config = self.get_config(ctx.guild.id)
        words = config.get("blocked_words", [])
        word = word.lower().strip()
        if word in words:
            words.remove(word)
            self.update_config(ctx.guild.id, {"blocked_words": words})
        await ctx.send(embed=discord.Embed(
            title="🗑️ Palavra Removida",
            description=f"`{word}` foi removida da lista.",
            color=discord.Color.orange()
        ))

    @automod.command(name="listwords")
    async def listwords(self, ctx):
        words = self.get_config(ctx.guild.id).get("blocked_words", [])
        text = "\n".join(f"• `{word}`" for word in words) or "Nenhuma palavra configurada."
        await ctx.send(embed=discord.Embed(
            title="📋 Palavras Bloqueadas",
            description=text[:4096],
            color=discord.Color.blue()
        ))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or self.is_exempt(message.author):
            return

        config = self.get_config(message.guild.id)
        if not config.get("automod_enabled", False):
            return

        content = message.content.lower()

        if config.get("filter_words", False):
            for word in config.get("blocked_words", []):
                if word.lower() in content:
                    try:
                        await message.delete()
                    except discord.HTTPException:
                        pass
                    await self.log(message.guild, "🛡️ AutoMod", f"Mensagem de {message.author.mention} removida por palavra bloqueada.")
                    return

        if config.get("filter_links", False):
            if re.search(r"(?:https?://|www\.|discord\.gg/|discord\.com/invite/)", content):
                try:
                    await message.delete()
                except discord.HTTPException:
                    pass
                await self.log(message.guild, "🛡️ AutoMod", f"Mensagem de {message.author.mention} removida por link.")
                return

        if config.get("anti_spam", False):
            key = (message.guild.id, message.author.id)
            now = time.monotonic()
            history = self.message_history[key]
            history.append(now)
            while history and now - history[0] > 8:
                history.popleft()
            if len(history) >= 6:
                try:
                    await message.delete()
                    await message.author.timeout(
                        discord.utils.utcnow() + discord.timedelta(seconds=60),
                        reason="AutoMod: spam"
                    )
                except Exception:
                    pass
                history.clear()
                await self.log(message.guild, "🛡️ Anti-Spam", f"{message.author.mention} foi detectado enviando mensagens rapidamente.")


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
