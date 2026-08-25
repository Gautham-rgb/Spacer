"""Hack Club Nest / Hugging Face Spaces entry point.

Nest expects an ``app.py`` at the repo root it can boot. This starts the
NiceGUI web app *and* any configured chat bots (Slack/Discord) on one server:
the web app owns the main thread, the bots run in background threads.
"""

import os
import sys

# Make the ``src`` layout importable when launched from the repo root.
_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from core.env import load_env
load_env()

from web.app import serve

if __name__ == "__main__":
    serve()
