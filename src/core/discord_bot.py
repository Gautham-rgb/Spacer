"""Discord front-end for Spacer, built on discord.py.

Mirrors the Slack bot: listens for ``!space`` / ``/space`` commands and replies
with rich Embeds. discord.py is imported lazily so Spacer still imports/works
without it installed. Set ``DISCORD_BOT_TOK`` in your environment to run it.

Note on the Message Content intent
-----------------------------------
``!space`` (a *prefix* command) needs Discord's privileged **Message Content**
intent, which you must toggle on in the Discord Developer Portal. If it isn't
enabled, Discord refuses the connection entirely. To stay robust we also expose
everything as **slash commands** (``/space``, ``/groq``), which work with *no*
special intent. If the prefix intent is missing we fall back to slash-only mode
so the bot always comes online.
"""

from __future__ import annotations

import asyncio
import os

import discord
from discord.ext import commands

from core.bot_base import dispatch
from core.env import load_env
from engine import SpaceEngine


class DiscordBot:
    """Interactive Discord bot for Spacer.

    Wraps :class:`~engine.SpaceEngine` behind a :class:`discord.ext.commands.Bot`
    that exposes every command both as a prefix (``!space``) and as a slash
    command (``/space``). The token comes from ``DISCORD_BOT_TOK`` (or ``.env``
    via :func:`core.env.load_env`). Call :meth:`run` to connect and block.
    """

    def __init__(self, token: str | None = None):
        load_env()
        self.token = token or os.environ.get("DISCORD_BOT_TOK")
        self.engine = SpaceEngine()
        self.bot = None

    def _build(self, message_content: bool = True) -> commands.Bot:
        intents = discord.Intents.default()
        intents.message_content = message_content
        bot = commands.Bot(command_prefix="!", intents=intents)

        @bot.event
        async def on_ready():
            print(f"Spacer Discord bot logged in as {bot.user}")
            # Make slash commands show up quickly (global sync can otherwise
            # take up to an hour to propagate).
            try:
                await bot.tree.sync()
                print("Synced slash commands.")
            except Exception as exc:  # never fatal
                print(f"Slash command sync failed: {exc}")

        @bot.hybrid_command(name="space", description="Show upcoming space events")
        async def space(ctx: commands.Context, *, cmd: str = ""):
            result = dispatch(self.engine, cmd.strip())
            if not result.discord_embeds:
                await ctx.send("No results.")
                return
            for embed_data in result.discord_embeds:
                await ctx.send(embed=self._to_embed(embed_data))

        @bot.hybrid_command(name="groq", description="Ask the Groq assistant")
        async def groq_cmd(ctx: commands.Context, *, question: str = ""):
            from core.groq_chat import clear_conversation, groq_chat

            question = (question or "").strip()
            key = f"{ctx.author.id}@{ctx.channel.id}"
            if question.lower() in ("reset", "clear"):
                await ctx.send("Conversation cleared — Groq starts fresh.")
                clear_conversation(key)
                return
            if not question:
                await ctx.send("Ask me something — `/groq <your question>`")
                return
            try:
                await ctx.defer()
            except Exception:  # noqa: BLE001 - deferral is best-effort
                pass
            answer = await asyncio.to_thread(groq_chat, question, key=key)
            await ctx.send(answer)

        return bot

    @staticmethod
    def _to_embed(data: dict) -> discord.Embed:
        embed = discord.Embed(
            title=data.get("title"),
            description=data.get("description"),
            color=data.get("color", 0x2B6CB0),
        )
        for field in data.get("fields", []):
            embed.add_field(
                name=field.get("name", ""),
                value=field.get("value", ""),
                inline=field.get("inline", False),
            )
        return embed

    def run(self) -> None:
        if not self.token:
            raise RuntimeError(
                "Missing Discord token. Set DISCORD_BOT_TOK in your environment."
            )

        # Run our own loop instead of ``bot.run()``. discord.py's run()
        # installs SIGINT/SIGTERM handlers, which can only be set in the main
        # thread — calling it from a daemon thread (as web/app.py does) raises
        # ``ValueError: signal only works in main thread`` on Linux and the bot
        # silently never connects. ``bot.start`` doesn't touch signals.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            self.bot = self._build(message_content=True)
            try:
                loop.run_until_complete(self.bot.start(self.token))
            except discord.PrivilegedIntentsRequired:
                # Message Content intent isn't enabled in the portal — drop the
                # prefix intent and reconnect in slash-only mode so the bot
                # still works.
                print(
                    "Message Content intent not enabled in the Discord Developer "
                    "Portal; falling back to slash commands only (/space, /groq). "
                    "Enable the intent to also use the !space prefix."
                )
                self.bot = self._build(message_content=False)
                loop.run_until_complete(self.bot.start(self.token))
        except KeyboardInterrupt:
            if self.bot is not None:
                loop.run_until_complete(self.bot.close())
        finally:
            loop.close()
