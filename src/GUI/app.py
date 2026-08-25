"""Desktop GUI for Spacer, built with ttkbootstrap (native window).

A classic native desktop window (no browser required) that shows the live
timeline and lets you filter. It is a thin view over ``SpaceEngine.get_events``
— no fetching logic lives here (roadmap Phase 1). Desktop notifications are
wired through the existing :class:`~core.notifier.Notifier`.

Run with::

    spacer-gui        # or:  python -m gui.app
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime, timedelta, timezone

import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledText

from engine import SpaceEngine
from version import __version__

TRACKS = ["all", "space_weather", "space_events", "probe_launch", "probe_events"]


class SpacerGUI:
    """Native ttkbootstrap window bound to a :class:`~engine.SpaceEngine`.

    Builds a control strip (track / date range / name / limit), a results
    tree, and a status line. ``refresh`` repopulates the tree from
    ``engine.get_events``; ``notify_upcoming`` runs the engine's notify action.
    """

    def __init__(self, root: ttk.Window, engine: SpaceEngine | None = None):
        self.root = root
        self.engine = engine or SpaceEngine()
        self.root.title(f"Spacer v{__version__}")
        self.root.geometry("900x600")

        self._build_controls()
        self._build_tree()
        self.refresh()

    def _build_controls(self) -> None:
        ctrl = ttk.Frame(self.root, padding=10)
        ctrl.pack(fill="x")

        ttk.Label(ctrl, text="Track:").grid(row=0, column=0, sticky="w", padx=2)
        self.track = ttk.Combobox(ctrl, values=TRACKS, state="readonly", width=18)
        self.track.set("all")
        self.track.grid(row=0, column=1, padx=2)

        ttk.Label(ctrl, text="After:").grid(row=0, column=2, sticky="w", padx=2)
        self.after = ttk.Entry(ctrl, width=12)
        self.after.grid(row=0, column=3, padx=2)

        ttk.Label(ctrl, text="Before:").grid(row=0, column=4, sticky="w", padx=2)
        self.before = ttk.Entry(ctrl, width=12)
        self.before.grid(row=0, column=5, padx=2)

        ttk.Label(ctrl, text="Name:").grid(row=1, column=0, sticky="w", padx=2, pady=4)
        self.name = ttk.Entry(ctrl, width=18)
        self.name.grid(row=1, column=1, padx=2, pady=4)

        ttk.Label(ctrl, text="Limit:").grid(row=1, column=2, sticky="w", padx=2, pady=4)
        self.limit = ttk.Spinbox(ctrl, from_=1, to=200, width=8)
        self.limit.set(20)
        self.limit.grid(row=1, column=3, padx=2, pady=4)

        ttk.Button(ctrl, text="Refresh", command=self.refresh,
                   bootstyle="success").grid(row=1, column=4, padx=4, pady=4)
        ttk.Button(ctrl, text="Notify upcoming", command=self.notify_upcoming,
                   bootstyle="info").grid(row=1, column=5, padx=4, pady=4)

    def _build_tree(self) -> None:
        cols = ("time", "countdown", "category", "title", "info")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", height=20)
        self.tree.heading("time", text="Time (UTC)")
        self.tree.heading("countdown", text="Countdown")
        self.tree.heading("category", text="Category")
        self.tree.heading("title", text="Title")
        self.tree.heading("info", text="Info")
        self.tree.column("time", width=150)
        self.tree.column("countdown", width=90)
        self.tree.column("category", width=110)
        self.tree.column("title", width=200)
        self.tree.column("info", width=320)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.status = ttk.Label(self.root, text="", padding=4)
        self.status.pack(fill="x")

    def _parse(self, s: str) -> datetime | None:
        s = (s or "").strip()
        if not s:
            return None
        try:
            return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def refresh(self) -> None:
        events = self.engine.get_events(
            track=self.track.get(),
            after=self._parse(self.after.get()),
            before=self._parse(self.before.get()),
            name=self.name.get().strip() or None,
            limit=int(self.limit.get() or 20),
        )
        self.tree.delete(*self.tree.get_children())
        for ev in sorted(events, key=lambda e: e.get("time") or 0):
            ev_time = ev.get("time")
            ts = ev_time.strftime("%Y-%m-%d %H:%M") if ev_time else "Unknown"
            self.tree.insert("", "end", values=(
                ts,
                ev.get("countdown") or "T-?",
                str(ev.get("category", "EVENT")).upper(),
                ev.get("title", "Untitled"),
                (ev.get("info", "") or "")[:80],
            ))
        self.status.configure(text=f"Showing {len(events)} event(s).")

    def notify_upcoming(self) -> None:
        """Run the engine's notify action for the current filter (next hour)."""
        now = datetime.now(timezone.utc)
        self.engine.run(
            track=self.track.get(),
            action="notify",
            after=now,
            before=now + timedelta(hours=1),
            name=self.name.get().strip() or None,
            limit=int(self.limit.get() or 20),
        )
        self.status.configure(text="Checked for upcoming events to notify.")


def main() -> None:
    root = ttk.Window(themename="darkly")
    SpacerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
