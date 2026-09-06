"""Single source of truth for the Spacer version.

The number lives in ``[project].version`` in ``pyproject.toml``. At runtime we
read it straight from that file when a checkout is present (most accurate for
development); for installed packages we fall back to ``importlib.metadata`` as
reported through ``pip``.
"""

from __future__ import annotations

import os

PROJECT_NAME = "spacer-bot"


def _from_metadata() -> str:
    try:
        from importlib import metadata
        return metadata.version(PROJECT_NAME)
    except Exception:  # noqa: BLE001 - not installed / broken metadata
        return ""


def _from_pyproject() -> str:
    """Read ``[project].version`` out of the nearest pyproject.toml."""
    import tomllib

    module_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(module_dir)
    for candidate in (os.path.join(repo_root, "pyproject.toml"), "pyproject.toml"):
        try:
            with open(candidate, "rb") as fh:
                return str(tomllib.load(fh)["project"]["version"])
        except (OSError, KeyError, ValueError, tomllib.TOMLDecodeError):
            continue
    return ""


__version__ = _from_pyproject() or _from_metadata() or "0.0.0"