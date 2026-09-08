"""Timeline formatter output: CLI layout and Markdown rendering."""

from datetime import datetime, timezone

from core.formatter import TimelineFormatter


def _events():
    when = datetime(2026, 9, 12, 3, 30, tzinfo=timezone.utc)
    return [
        {"time": when, "title": "Falcon 9 Launch", "category": "Probe",
         "info": "Payload to orbit", "countdown": "T-4d"},
    ]


def test_render_cli_layout(capsys):
    TimelineFormatter().render_cli(_events())
    out = capsys.readouterr().out
    assert "^ LIVE PRODUCTION EVENT GRAPH" in out
    assert "=" * 70 in out
    assert "[PROBE]" in out
    assert "Falcon 9 Launch" in out
    assert "(T-4d)" in out


def test_render_cli_missing_fields_do_not_crash(capsys):
    ev = [{"time": datetime(2026, 9, 12, tzinfo=timezone.utc), "title": "Bare"}]
    TimelineFormatter().render_cli(ev)
    out = capsys.readouterr().out
    assert "Bare" in out
    assert "[EVENT]" in out


def test_render_cli_empty(capsys):
    TimelineFormatter().render_cli([])
    assert "No events" in capsys.readouterr().out


def test_render_markdown():
    md = TimelineFormatter().render_markdown(_events())
    assert "Falcon 9 Launch" in md
    assert "[PROBE]" in md
    assert "T-4d" in md


def test_render_markdown_empty():
    assert TimelineFormatter().render_markdown([]) == "No events found for this timeframe."