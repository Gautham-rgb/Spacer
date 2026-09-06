"""Read ``[tool.spacer.*]`` configuration from ``pyproject.toml``.

Keeps runtime-tunable settings (timeline format templates, web palette, home
track cards) in one obvious place while still working when the file is absent
or unparseable: everything has a sane built-in default. Requires Python 3.11+
for :mod:`tomllib`.
"""

from __future__ import annotations

import os
import tomllib
from functools import lru_cache

_DEFAULTS: dict[str, dict] = {
    # CLI / markdown timeline format templates ({key} placeholders are filled at
    # render time; unknown keys become empty strings).
    "formats": {
        "cli_title": "LIVE PRODUCTION EVENT GRAPH",
        "cli_header": "[{when}] ({countdown})",
        "cli_line": " |-- [{category}] {title}",
        "cli_info": "      {info}",
        "md_line": "• **[{category}]** {title}\n  `{when}` ({countdown})\n  _{info}",
    },
    "web": {
        "site_name": "Spacer",
        "bg_color": "#070b16",
        "panel_color": "#0e1526",
        "border_color": "#1d2839",
        "accent": "#5898d4",
    },
    "tracks": {
        "space_weather": {"label": "Space Weather", "icon": "storm",
                          "desc": "Solar storms and K-index forecasts from NOAA."},
        "space_events": {"label": "Planetary Alignments", "icon": "auto_awesome",
                         "desc": "Conjunctions and 180° alignments of the planets."},
        "probe_launch": {"label": "Rocket Launches", "icon": "rocket_launch",
                         "desc": "Upcoming launches from around the world."},
        "probe_events": {"label": "Probe Missions", "icon": "satellite_alt",
                         "desc": "Missions and probes on their way through space."},
    },
}


def _find_pyproject() -> str:
    """Locate ``pyproject.toml``: env override, then current dir, then parents."""
    override = os.environ.get("SPACER_CONFIG")
    if override:
        return override

    directory = os.path.abspath(os.getcwd())
    while True:
        candidate = os.path.join(directory, "pyproject.toml")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    # Fall back to the config module's own source dir (repo checkout layout).
    module_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(module_dir))
    return os.path.join(repo_root, "pyproject.toml")


@lru_cache(maxsize=1)
def load_pyproject() -> dict:
    path = _find_pyproject()
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def spacer_sections() -> dict:
    return load_pyproject().get("tool", {}).get("spacer", {})


def spacer_section(name: str) -> dict:
    """Return the ``[tool.spacer.<name>]`` table merged over its defaults."""
    base = dict(_DEFAULTS.get(name, {}))
    user = spacer_sections().get(name, {})
    base.update(user)
    return base