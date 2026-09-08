"""Desktop GUI smoke: opens a withdrawn window and drives the pages.

Targeted at real desktop machines (Windows/macOS) where Tk is available; the
test is opt-in via ``-m gui`` because it needs a display.
"""

import time
from datetime import datetime, timezone

import pytest

pytest.importorskip("ttkbootstrap")

import ttkbootstrap as ttk
from gui.app import SpacerGUI


class _FakeEngine:
    def get_events(self, **kwargs):
        return [
            {"time": datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc), "countdown": "T-2h",
             "category": "SOLAR_FLARE", "title": "Flare C1.1",
             "info": "GOES-18 peak flux."},
            {"time": datetime(2026, 9, 7, 3, 0, tzinfo=timezone.utc), "countdown": "T-17h",
             "category": "K_INDEX", "title": "K-Index 5 (predicted)",
             "info": "Geomagnetic storm watch."},
        ]


@pytest.mark.gui
def test_gui_navigate_pages():
    root = ttk.Window(themename="darkly")
    root.withdraw()
    gui = SpacerGUI(root, _FakeEngine())
    gui._open_track("space_weather")
    deadline = time.time() + 3
    while time.time() < deadline and not gui._events:
        root.update()
        time.sleep(0.05)

    assert len(gui._events) == 2
    assert gui._count.cget("text") == "Events (2)"

    gui._open_detail(0)
    assert gui._d_title.cget("text") == "Flare C1.1"
    gui._next()
    assert gui._idx == 1
    assert gui._prev_btn.instate(["!disabled"])
    gui._next()
    assert gui._idx == 1  # clamped at the end
    gui._prev()
    assert gui._idx == 0

    gui._auto_var.set(True)
    gui._on_auto_toggle()
    assert gui._auto_job is not None
    gui._show("home")
    gui._on_close()