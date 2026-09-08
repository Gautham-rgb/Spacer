"""Thin wrapper around the Groq chat API for Spacer's chat commands.

Used by the Slack/Discord bots (``!groq`` / ``!ask``) and the web UI. The
client is created lazily so it works whether or not ``.env`` has been loaded
yet, and so importing this module never fails when ``groq`` is missing.
"""

from __future__ import annotations

import os
from collections import OrderedDict

from core.config import GROQ_API_KEY, GROQ_MODEL

GROQ_CHAT_MODEL = GROQ_MODEL
_SYSTEM = (
    "You are a space enthusiast's assistant: friendly, concise, and focused on space, "
    "astronomy, and science when relevant. "
    "Don't use Markdown; use plain text and numbered lists if helpful."
)

# Keep the last N question/answer pairs per conversation key so the model can
# follow up on earlier context ("what about its booster?" style questions).
_MAX_TURNS = 6
_MAX_KEYS = 100

_client = None
_conversations: "OrderedDict[str, list[dict]]" = OrderedDict()


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


def clear_conversation(key: str) -> None:
    """Forget the stored chat history for ``key`` (per user/channel)."""
    if key:
        _conversations.pop(key, None)


def conversation_length(key: str) -> int:
    return len(_conversations.get(key, [])) // 2


def groq_chat(prompt: str, *, key: str | None = None, reset: bool = False,
              max_tokens: int = 1024, system: str | None = None) -> str:
    if not prompt or not prompt.strip():
        return "Ask me something — e.g. `what's the next launch?`"
    client = _get_client()
    if client is None:
        return "Groq isn't configured on this server (set GROQ_API_KEY)."
    if reset and key:
        clear_conversation(key)
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        elif _SYSTEM:
            messages.append({"role": "system", "content": _SYSTEM})
        if key:
            messages.extend(_conversations.get(key, []))
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=GROQ_CHAT_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7,
        )
        answer = str(resp.choices[0].message.content).strip()
        if key:
            history = _conversations.setdefault(key, [])
            history.append({"role": "user", "content": prompt})
            history.append({"role": "assistant", "content": answer})
            _conversations[key] = history[-(_MAX_TURNS * 2):]
            _conversations.move_to_end(key)  # mark most-recently-used
            if len(_conversations) > _MAX_KEYS:  # bound memory across many rooms
                _conversations.popitem(last=False)  # evict least-recently-used
        return answer
    except Exception as exc:
        return f"Groq error: {exc}"
