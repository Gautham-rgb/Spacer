"""Thin wrapper around the Groq chat API for Spacer's chat commands.

Used by the Slack/Discord bots (``!groq`` / ``!ask``) and the web UI. The
client is created lazily so it works whether or not ``.env`` has been loaded
yet, and so importing this module never fails when ``groq`` is missing.
"""

from __future__ import annotations

import os

from core.config import GROQ_API_KEY, GROQ_MODEL

GROQ_CHAT_MODEL = GROQ_MODEL
_SYSTEM = (
    "You are a space enthusiast's assistant: friendly, concise, and focused on space, "
    "astronomy, and science when relevant. "
    "Don't use Markdown; use plain text and numbered lists if helpful."
)

_client = None


def _get_client():
    global _client
    if _client is None:
        key = os.environ.get("GROQ_API_KEY") or GROQ_API_KEY
        if not key:
            return None
        try:
            from groq import Groq
            _client = Groq(api_key=key)
        except Exception:  # noqa: BLE001 - never let a bad key crash import
            _client = None
    return _client


def groq_available() -> bool:
    return _get_client() is not None


def groq_chat(prompt: str, *, max_tokens: int = 400, system: str | None = None) -> str:
    if not prompt or not prompt.strip():
        return "Ask me something — e.g. `what's the next launch?`"
    client = _get_client()
    if client is None:
        return "Groq isn't configured on this server (set GROQ_API_KEY)."
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        elif _SYSTEM:
            messages.append({"role": "system", "content": _SYSTEM})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=GROQ_CHAT_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return str(resp.choices[0].message.content).strip()
    except Exception as exc:
        return f"Groq error: {exc}"
