"""Bot command dispatch: parsing, aliases, flags, and groq routing."""

import core.groq_chat as groq_chat_mod
from version import __version__
from core.bot_base import HELP_TEXT, dispatch


class _FakeEngine:
    def __init__(self):
        self.calls = []

    def get_events(self, **kwargs):
        self.calls.append(kwargs)
        return []


def _last(engine):
    return engine.calls[-1] if engine.calls else {}


def test_help_for_empty_and_alias():
    engine = _FakeEngine()
    assert dispatch(engine, "help").plain == HELP_TEXT
    assert dispatch(engine, "h").plain == HELP_TEXT
    result = dispatch(engine, "")
    assert result.plain == HELP_TEXT
    assert engine.calls == []


def test_version():
    engine = _FakeEngine()
    result = dispatch(engine, "version")
    assert f"v{__version__}" in result.plain


def test_list_flags_parsed_anywhere():
    engine = _FakeEngine()
    result = dispatch(engine, "list probe_events --limit 5 --name falcon")
    assert result.slack_blocks
    assert _last(engine)["track"] == "probe_events"
    assert _last(engine)["limit"] == 5
    assert _last(engine)["name"] == "falcon"


def test_list_short_flags_and_bare_track():
    engine = _FakeEngine()
    dispatch(engine, "probe_launch -l 3")
    assert _last(engine)["track"] == "probe_launch"
    assert _last(engine)["limit"] == 3
    engine.calls.clear()
    dispatch(engine, "list")
    assert _last(engine)["track"] == "all"


def test_weather_alias_maps_to_space_weather():
    engine = _FakeEngine()
    dispatch(engine, "weather")
    assert _last(engine)["track"] == "space_weather"


def _fake_events(n: int) -> list[dict]:
    from datetime import datetime, timezone
    return [{"title": f"Event {i}", "info": "x", "category": "TEST",
             "time": datetime(2030, 1, i % 28 + 1, tzinfo=timezone.utc)}
            for i in range(n)]


def test_list_output_respects_limit_and_summary_shows_flags():
    engine = _FakeEngine()
    engine.get_events = lambda **kw: _fake_events(3)
    res = dispatch(engine, "probe_launch --limit 3 --name falcon")
    assert "Spacer timeline (probe_launch)" in res.plain
    assert "falcon" in res.plain and "limit 3" in res.plain
    sections = [b for b in res.slack_blocks if b.get("type") == "section"]
    assert len(sections) == 3
    assert not any("more" in b["text"]["text"] for b in sections)
    assert len(res.discord_embeds) == 4  # summary header + 3 events


def test_list_truncation_note_when_limit_large():
    engine = _FakeEngine()
    engine.get_events = lambda **kw: _fake_events(50)
    res = dispatch(engine, "list --limit 50")
    sections = [b for b in res.slack_blocks if b.get("type") == "section"]
    assert len(sections) == 26  # 25 event blocks + 1 "25 more" note
    assert any("more" in b["text"]["text"] and "25" in b["text"]["text"]
               for b in sections)
    embeds = res.discord_embeds
    assert len(embeds) == 12  # summary header + 10 cap + truncation note


def test_launches_alias_maps_to_probe_launch():
    engine = _FakeEngine()
    dispatch(engine, "launches")
    assert _last(engine)["track"] == "probe_launch"


def test_groq_question_uses_memory(monkeypatch):
    engine = _FakeEngine()
    calls = []

    def fake_chat(prompt, **kwargs):
        calls.append((prompt, kwargs))
        return "REPLY"

    monkeypatch.setattr(groq_chat_mod, "groq_chat", fake_chat)
    result = dispatch(engine, "groq what is the next launch?")
    assert result.plain == "REPLY"
    assert calls[0][0] == "what is the next launch?"
    assert calls[0][1]["key"] == "shared"


def test_groq_scoped_per_channel_and_user(monkeypatch):
    engine = _FakeEngine()
    calls = []
    monkeypatch.setattr(groq_chat_mod, "groq_chat",
                        lambda prompt, **kw: calls.append((prompt, kw)) or "ok")
    dispatch(engine, "groq hi", context={"channel": "C1", "user": "U1"})
    dispatch(engine, "groq hi again", context={"channel": "C1", "user": "U1"})
    assert len(calls) == 2
    assert calls[0][1]["key"] == calls[1][1]["key"] == "U1@C1"


def test_groq_reset_clears_memory(monkeypatch):
    engine = _FakeEngine()
    cleared = []
    monkeypatch.setattr(groq_chat_mod, "groq_chat", lambda *a, **k: "x")
    monkeypatch.setattr(groq_chat_mod, "clear_conversation",
                        lambda key: cleared.append(key))
    result = dispatch(engine, "groq reset", context={"channel": "C", "user": "U"})
    assert "cleared" in result.plain.lower()
    assert cleared == ["U@C"]


def test_groq_empty_question_hint():
    engine = _FakeEngine()
    result = dispatch(engine, "groq")
    assert "Ask me something" in result.plain