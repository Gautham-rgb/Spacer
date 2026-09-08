"""CLI argument parsing + events/show output (engine stubbed)."""

import argparse
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import engine as engine_mod
from CLI_bot import CLI


class _FakeSpaceEngine:
    formatter = SimpleNamespace(
        render_cli=lambda events: print("CLI timeline"),
        render_markdown=lambda events: "MD timeline",
    )

    def __init__(self, events=None):
        self._events = events or []

    def get_events(self, **kwargs):
        return list(self._events)


def _ev(title="Falcon 9 : Starlink", category="Probe"):
    return {"time": datetime(2026, 9, 12, 3, 30, tzinfo=timezone.utc),
            "title": title, "category": category, "info": "payload", "countdown": "T-4d"}


def _patch_engine(monkeypatch, events):
    """Make ``SpaceEngine()`` inside the CLI return a canned fake."""
    fake = _FakeSpaceEngine(events)
    monkeypatch.setattr(engine_mod, "SpaceEngine", Mock(return_value=fake))


def test_parse_cli_date_valid():
    assert CLI.parse_cli_date("2026-09-12") == datetime(2026, 9, 12, tzinfo=timezone.utc)


def test_parse_cli_date_rejects_garbage():
    with pytest.raises(argparse.ArgumentTypeError):
        CLI.parse_cli_date("not-a-date")


def test_parser_events_list_flags():
    args = CLI.build_parser().parse_args(
        ["events", "list", "space_weather", "--limit", "5", "-F", "json", "--name", "storm"])
    assert args.track == "space_weather"
    assert args.limit == 5
    assert args.format == "json"
    assert args.name == "storm"


def test_parser_tolerates_bare_help():
    with pytest.raises(SystemExit):
        CLI.build_parser().parse_args(["--help"])


def test_window_defaults_to_last_day_plus_two_weeks():
    now = datetime.now(timezone.utc)
    after, before = CLI._window(None, None)
    assert after <= now
    assert now + timedelta(days=13) <= before <= now + timedelta(days=15)


def test_list_events_json(monkeypatch, capsys):
    _patch_engine(monkeypatch, [_ev()])
    rc = CLI.list_events(SimpleNamespace(
        track="probe_launch", after=None, before=None, name=None, limit=5, format="json"))
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["title"] == "Falcon 9 : Starlink"
    assert payload[0]["time"].startswith("2026-09-12")


def test_show_event_by_index(monkeypatch, capsys):
    _patch_engine(monkeypatch, [_ev()])
    rc = CLI.show_event(SimpleNamespace(
        track="probe_launch", selector="1", after=None, before=None, name=None, limit=5))
    assert rc == 0
    assert "Falcon 9 : Starlink" in capsys.readouterr().out


def test_show_event_index_out_of_range(monkeypatch, capsys):
    _patch_engine(monkeypatch, [_ev()])
    rc = CLI.show_event(SimpleNamespace(
        track="probe_launch", selector="9", after=None, before=None, name=None, limit=5))
    assert rc == 2


def test_show_event_substring_unique(monkeypatch, capsys):
    _patch_engine(monkeypatch, [_ev()])
    rc = CLI.show_event(SimpleNamespace(
        track="probe_launch", selector="starlink", after=None, before=None, name=None, limit=5))
    assert rc == 0
    assert "Title:    Falcon 9 : Starlink" in capsys.readouterr().out


def test_show_event_substring_ambiguous(monkeypatch, capsys):
    _patch_engine(monkeypatch,
                  [_ev("Falcon 9 : Starlink 6-40"), _ev("Falcon 9 : Starlink 6-41")])
    rc = CLI.show_event(SimpleNamespace(
        track="probe_launch", selector="starlink", after=None, before=None, name=None, limit=5))
    assert rc == 2
    assert "disambiguate" in capsys.readouterr().out
