"""Discord front-end for Spacer, built on discord.py.

Mirrors the Slack bot: listens for ``!space`` commands and replies with rich
Embeds. ``discord.py`` is imported lazily so Spacer still imports/works
without it installed. Set ``DISCORD_BOT_TOK`` in your environment to run it.
"""

from __future__ import annotations

import os

from core.env import load_env
from core.bot_base import dispatch
from engine import SpaceEngine


class DiscordBot:
    """Interactive Discord bot for Spacer.

    Wraps :class:`~engine.SpaceEngine` behind a :class:`discord.Client` that
    reacts to ``!space``-prefixed messages. The token comes from
    ``DISCORD_BOT_TOK`` (or ``.env`` via :func:`core.env.load_env`). Call
    :meth:`run` to connect and block.
    """

    def __init__(self, token: str | None = None):
        load_env()
        self.token = token or os.environ.get("DISCORD_BOT_TOK")
        self.engine = SpaceEngine()
        self.client = None

    def _ensure_client(self):
        if not self.token:
            raise RuntimeError(
                "Missing Discord token. Set DISCORD_BOT_TOK in your environment."
            )
        try:
            import discord
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "discord.py is required for the Discord bot. Install with "
                "`pip install discord.py`."
            ) from exc

        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)

        @self.client.event
        async def on_ready():
            print(f"Spacer Discord bot logged in as {self.client.user}")

        @self.client.event
        async def on_message(message):
            if message.author == self.client.user:
                return
            content = message.content.strip()
            if not content.lower().startswith("!space"):
                return
            cmd = content[len("!space"):].strip()
            result = dispatch(self.engine, cmd)
            for embed_data in result.discord_embeds:
                await message.channel.send(embed=self._to_embed(embed_data))

    @staticmethod
    def _to_embed(data: dict):
        import discord
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
        self._ensure_client()
        assert self.token is not None
        self.client.run(self.token)
