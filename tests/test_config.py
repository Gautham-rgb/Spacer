"""Default config, pyproject loading, version, track cards."""

import os
import re

import pytest

from core import config
from core.pyproject import spacer_section, track_cards
from version import __version__


def test_track_catalog_is_consistent():
    assert config.TRACKS[0] == "all"
    assert config.TRACK_NAMES == config.TRACKS[1:]
    assert "probe_launch" in config.TRACKS
    assert "space_weather" in config.TRACKS


def test_formats_merge_over_defaults():
    fmt = spacer_section("formats")
    assert fmt["cli_title"] == "LIVE PRODUCTION EVENT GRAPH"
    assert "{title}" in fmt["cli_line"]


def test_web_palette_has_all_keys():
    web = spacer_section("web")
    for key in ("site_name", "bg_color", "panel_color", "border_color", "accent"):
        assert web[key]


def test_track_cards_match_track_names():
    cards = track_cards()
    assert [c["track"] for c in cards] == config.TRACK_NAMES
    for card in cards:
        assert card["label"] and card["icon"]
        assert "desc" in card


def test_track_cards_fall_back_for_unknown_tracks(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.spacer.tracks.space_weather]\nlabel = 'Custom'\nicon = 'star'\n"
        "desc = 'mine'\n\n[tool.spacer.tracks.mystery_track]\n"
        "sub = 'whatever'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SPACER_CONFIG", str(pyproject))
    from core.pyproject import load_pyproject
    load_pyproject.cache_clear()
    cards = track_cards()
    assert cards[0]["label"] == "Custom"
    assert cards[0]["icon"] == "star"
    monkeypatch.delenv("SPACER_CONFIG", raising=False)
    load_pyproject.cache_clear()


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)