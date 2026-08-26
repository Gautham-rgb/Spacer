"""Slack front-end for Spacer, built on Socket Mode.

Connects over Socket Mode, listens for ``!space`` commands in any channel it
can see, and replies with Block Kit messages. ``slack_sdk`` is imported
lazily so Spacer still imports/works without it installed.
"""

from __future__ import annotations

import os
import re

from core.bot_base import dispatch
from core.env import load_env
from engine import SpaceEngine


class SlackBot:
    """Interactive Slack app for Spacer.

    Wraps :class:`~engine.SpaceEngine` behind a Socket Mode listener. Credentials
    come from ``SLACK_BOT_TOK`` / ``SLACK_APP_TOK`` (see ``.env``). Call
    :meth:`run` to connect; it blocks while listening for ``!space`` commands.
    """

    def __init__(self, bot_token: str | None = None, app_token: str | None = None):
        load_env()
        self.bot_token = bot_token or os.environ.get("SLACK_BOT_TOK")
        self.app_token = app_token or os.environ.get("SLACK_APP_TOK")
        self.engine = SpaceEngine()
        self.client = None

    def _ensure_client(self):
        if not self.bot_token or not self.app_token:
            raise RuntimeError(
                "Missing Slack credentials. Set SLACK_BOT_TOK and SLACK_APP_TOK "
                "in your environment (see .env)."
            )
        try:
            from slack_sdk.web import WebClient
            from slack_sdk.socket_mode import SocketModeClient
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "slack_sdk is required for the Slack bot. Install with "
                "`pip install slack_sdk`."
            ) from exc

        self.client = SocketModeClient(
            app_token=self.app_token,
            web_client=WebClient(token=self.bot_token),
        )
        self.client.socket_mode_request_listeners.append(self._on_request)

    def _reply(self, channel: str, blocks) -> None:
        self.client.web_client.chat_postMessage(
            channel=channel, text="Spacer", blocks=blocks
        )

    def _on_request(self, client, req) -> None:
        from slack_sdk.socket_mode.response import SocketModeResponse

        try:
            if req.type == "events_api":
                event = req.payload.get("event", {})
                if event.get("type") == "message" and "subtype" not in event:
                    text = event.get("text", "")
                    low = text.lower()
                    channel = event.get("channel", "")
                    if low.startswith("!space"):
                        cmd = re.sub(r"^!space\s*", "", text, flags=re.I).strip()
                        result = dispatch(self.engine, cmd)
                        self._reply(channel, result.slack_blocks)
                    elif low.startswith(("!groq", "!ask", "!ai")):
                        prompt = re.sub(r"^!(groq|ask|ai)\s*", "", text, flags=re.I).strip()
                        from core.groq_chat import groq_chat
                        answer = groq_chat(prompt) if prompt else "Usage: !groq <question>"
                        self._reply(channel, [{
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": answer[:2900]},
                        }])
        finally:
            client.send_socket_mode_response(
                SocketModeResponse(envelope_id=req.envelope_id)
            )

    def run(self) -> None:
        self._ensure_client()
        print("Spacer Slack bot connected (Socket Mode). Listening for !space commands...")
        self.client.connect()
