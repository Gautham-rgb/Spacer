"""Best-effort PyPI version check (stdlib only, no extra dependency).

Mirrors the Kerbal Gravity Program ``updates.py`` pattern: a single
``PYPI_URL`` is queried with nothing but :mod:`urllib`, and every network or
JSON error is swallowed so the CLI never breaks because PyPI is unreachable.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from version import PROJECT_NAME, __version__

PYPI_URL = f"https://pypi.org/pypi/{PROJECT_NAME}/json"
_USER_AGENT = f"{PROJECT_NAME}-update-check"


def _parse_version(v: str) -> tuple[int, ...]:
    """Loose numeric parse good enough for '0.2.4' style versions."""
    parts: list[int] = []
    for chunk in str(v).split("."):
        num = ""
        for ch in chunk:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    return tuple(parts)


def get_latest_version(timeout: float = 5.0) -> str:
    """Return the latest version string published on PyPI for this project."""
    req = urllib.request.Request(
        PYPI_URL, headers={"User-Agent": _USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return str(data["info"]["version"])


def is_update_available(current: str, latest: str | None) -> bool:
    if not latest:
        return False
    try:
        return _parse_version(latest) > _parse_version(current)
    except Exception:
        return False


def check_for_update(timeout: float = 5.0, *, notify_error: bool = True) -> str:
    """Return a human-readable update status line (never raises).

    ``notify_error=False`` turns network failures into an empty string so
    callers that render this next to a UI (e.g. the web header) can stay clean
    instead of showing "Could not reach PyPI".
    """
    try:
        latest = get_latest_version(timeout=timeout)
    except Exception as exc:  # network/JSON errors must never break the caller
        if not notify_error:
            return ""
        return f"Could not reach PyPI to check for updates ({exc})."
    if is_update_available(__version__, latest):
        return (
            f"A newer version is available: v{latest} "
            f"(you have v{__version__}). Upgrade: "
            f"pip install --upgrade {PROJECT_NAME}"
        )
    return f"You're up to date (latest on PyPI is v{latest})."
