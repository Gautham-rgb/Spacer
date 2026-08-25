"""Load ``.env`` into ``os.environ`` if python-dotenv is available.

The Slack/Discord tokens and API keys live in ``.env`` (gitignored). Call
:func:`load_env` once at startup so the rest of the code can read them via
``os.environ.get(...)``. If ``python-dotenv`` isn't installed, this is a
no-op (the vars are then expected to be real environment variables, e.g. on
Hack Club Nest secrets).
"""

from __future__ import annotations

import os


def load_env(path: str = ".env") -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    # Don't clobber real env vars that are already set (Nest secrets, CI, ...).
    load_dotenv(path, override=False)
