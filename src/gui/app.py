"""Desktop GUI for Spacer (native ttkbootstrap window), mirroring the web app.

The flow matches the web app exactly:

  home (track cards) -> track timeline (filters + auto-refresh, clickable
  event cards) -> event detail page (prev/next navigation).

It is a thin view over :meth:`engine.SpaceEngine.get_events`, reusing the same
track metadata and dark-space palette that the web app reads from
``pyproject.toml``. Heavy fetches run on a background thread so the window
never freezes.

Run with::

    spacer-gui        # or:  python -m gui.app
"""

from __future__ import annotations

import queue
import threading
from datetime import datetime, timezone

import tkinter as tk
import ttkbootstrap as ttk
try:  # ttkbootstrap >=2.2 exposes ScrolledFrame at the top level
    from ttkbootstrap.scrolled import ScrolledFrame
except ModuleNotFoundError:  # pragma: no cover - older layout
    from ttkbootstrap import ScrolledFrame #type: ignore

from core.config import CATEGORY_STYLE, DEFAULT_CATEGORY_STYLE
from core.pyproject import spacer_section, track_cards
from engine import SpaceEngine
from version import __version__

# Material icon name -> desktop glyph (title-safe unicode, not emoji).
_GLYPHS = {
    "storm": "\u26A1",
    "auto_awesome": "\u2726",
    "rocket_launch": "\u25B2",
    "satellite_alt": "\u25CE",
}
_DEFAULT_GLYPH = "\u25C6"

_FONT = "Segoe UI"
_INTERVAL_CHOICES = (15, 30, 60)


def _cat_style(category: str | None) -> tuple[str, str]:
    return CATEGORY_STYLE.get(str(category or "").strip(), DEFAULT_CATEGORY_STYLE)


def _ts(ev: dict, fmt: str = "%Y-%m-%d %H:%M UTC") -> str:
    ev_time = ev.get("time")
    return ev_time.strftime(fmt) if ev_time else "Unknown"


class SpacerGUI:
    def __init__(self, root: ttk.Window, engine: SpaceEngine | None = None):
        self.root = root
        self.engine = engine or SpaceEngine()
        self.palette = spacer_section("web")
        self.cards = track_cards()

        self.root.title(f"{self.palette['site_name']} v{__version__}")
        self.root.geometry("980x700")
        self.root.minsize(760, 540)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._events: list[dict] = []
        self._idx = 0
        self._fetching = False
        self._auto_job = None
        self._poll_job = None
        self._q: "queue.Queue[tuple]" = queue.Queue()

        self._active_track = ""
        self._auto_var = ttk.BooleanVar(value=False)
        self._interval_var = ttk.IntVar(value=30)
        self._name_var = ttk.StringVar(value="")
        self._after_var = ttk.StringVar(value="")
        self._before_var = ttk.StringVar(value="")
        self._limit_var = ttk.IntVar(value=60)

        container = ttk.Frame(root, padding=10)
        container.pack(fill="both", expand=True)

        self._build_home(container)
        self._build_track(container)
        self._build_detail(container)
        self._show("home")

    # ---------------------------------------------------------------- pages
    def _show(self, name: str) -> None:
        self._stop_auto()
        for page in (self._home, self._track, self._detail):
            page.pack_forget()
        {"home": self._home, "track": self._track, "detail": self._detail}[name].pack(
            fill="both", expand=True)
        if name == "track":
            self._start_auto()

    # ---------------------------------------------------------------- labels
    def _label(self, parent, text="", *, size=10, bold=False, color="#d5dae3",
               side=None, anchor="w", wraplength=0):
        lbl = tk.Label(parent, text=text, font=(_FONT, size, "bold" if bold else "normal"),
                       bg=self.palette["panel_color"], fg=color, anchor=anchor,
                       justify="left", wraplength=wraplength)
        if side:
            lbl.pack(side=side, padx=6, pady=1)
        else:
            lbl.pack(fill="x", padx=6, pady=1)
        return lbl

    def _accent_chip(self, parent, text: str, *, bg: str, fg: str) -> tk.Label:
        chip = tk.Label(parent, text=text, font=(_FONT, 8, "bold"),
                        bg=bg, fg=fg, padx=8, pady=2)
        chip.pack(side="right", padx=6)
        return chip

    def _clickable(self, widget, command) -> None:
        widget.configure(cursor="hand2")
        for w in (widget, *self._walk(widget)):
            w.bind("<Button-1>", lambda _e, c=command: c())

    def _walk(self, widget):
        children = []
        for child in widget.winfo_children():
            children.append(child)
            children.extend(self._walk(child))
        return children

    # ----------------------------------------------------------------- home
    def _build_home(self, container) -> None:
        page = ttk.Frame(container)
        self._home = page

        tk.Label(page, text=self.palette["site_name"], bg="#070b16",
                 fg="#ffffff", font=(_FONT, 30, "bold")).pack(pady=(18, 0))
        tk.Label(page, text="Choose a track to explore.", bg="#070b16",
                 fg="#9aa4b2", font=(_FONT, 12)).pack(pady=(0, 18))

        body = tk.Frame(page, bg="#070b16")
        body.pack(fill="x", expand=True)

        for card in self.cards:
            self._home_card(body, card)

        tk.Label(page, text=f"{self.palette['site_name']} v{__version__} · desktop",
                 bg="#070b16", fg="#5a6472", font=(_FONT, 9)).pack(pady=(18, 8))

    def _home_card(self, body, card: dict) -> None:
        frame = tk.Frame(body, bg=self.palette["panel_color"], padx=18, pady=14,
                         highlightbackground=self.palette["border_color"],
                         highlightthickness=1)
        frame.pack(fill="x", padx=24, pady=6)
        self._label(frame, _GLYPHS.get(card["icon"], _DEFAULT_GLYPH), size=22,
                    color=self.palette["accent"], side="left")
        col = tk.Frame(frame, bg=self.palette["panel_color"])
        col.pack(side="left", fill="x", expand=True, padx=8)
        self._label(col, card["label"], size=15, bold=True, color="#edf1f7")
        self._label(col, card["desc"], size=10, color="#8b95a3")
        self._label(frame, "Explore \u2192", size=9, color=self.palette["accent"],
                    side="right")
        self._clickable(frame, lambda t=card["track"]: self._open_track(t))

    # ---------------------------------------------------------------- track
    def _build_track(self, container) -> None:
        page = ttk.Frame(container)
        self._track = page

        top = ttk.Frame(page)
        top.pack(fill="x", pady=(2, 4))
        ttk.Button(top, text="\u2190 Home", bootstyle="secondary-outline",
                   command=lambda: self._show("home")).pack(side="left")
        self._track_title = tk.Label(top, text="", bg="#070b16", fg="#ffffff",
                                     font=(_FONT, 18, "bold"))
        self._track_title.pack(side="left", padx=14)
        self._track_desc = tk.Label(top, text="", bg="#070b16", fg="#8b95a3",
                                    font=(_FONT, 10))
        self._track_desc.pack(side="left")

        filters = tk.Frame(page, bg=self.palette["panel_color"], padx=14, pady=10,
                           highlightbackground=self.palette["border_color"],
                           highlightthickness=1)
        filters.pack(fill="x", pady=6)
        self._fname = ttk.Entry(filters, textvariable=self._name_var, width=24)
        self._fafter = ttk.Entry(filters, textvariable=self._after_var, width=14)
        self._fbefore = ttk.Entry(filters, textvariable=self._before_var, width=14)
        self._flimit = ttk.Spinbox(filters, from_=1, to=300,
                                   textvariable=self._limit_var, width=8)
        for col, lbl, widget in (
                (0, "Name", self._fname),
                (1, "After (YYYY-MM-DD)", self._fafter),
                (2, "Before (YYYY-MM-DD)", self._fbefore),
                (3, "Limit", self._flimit)):
            ttk.Label(filters, text=lbl).grid(row=0, column=col * 2, sticky="w", padx=(0, 4))
            widget.grid(row=1, column=col * 2, sticky="w", padx=(0, 14))

        controls = ttk.Frame(page)
        controls.pack(fill="x", pady=4)
        self._count = ttk.Label(controls, text="Events")
        self._count.pack(side="left")
        ttk.Label(controls, text="every (s)").pack(side="right", padx=(12, 2))
        self._interval = ttk.Combobox(controls, values=list(_INTERVAL_CHOICES),
                                      textvariable=self._interval_var, width=6,
                                      state="readonly")
        self._interval.pack(side="right")
        self._auto_cb = ttk.Checkbutton(controls, text="Auto-refresh",
                                        variable=self._auto_var,
                                        command=self._on_auto_toggle)
        self._auto_cb.pack(side="right", padx=12)
        self._refresh_btn = ttk.Button(controls, text="Refresh",
                                       bootstyle="success",
                                       command=self.refresh)
        self._refresh_btn.pack(side="right", padx=(0, 12))

        self._status = ttk.Label(page, text="", bootstyle="default")
        self._status.pack(fill="x", pady=(2, 2))

        self._card_area = ScrolledFrame(page, autohide=True)
        self._card_area.pack(fill="both", expand=True)
        self._holder = ttk.Frame(self._card_area)
        self._holder.pack(fill="x", expand=True)

    def _render_cards(self) -> None:
        for widget in self._holder.winfo_children():
            widget.destroy()

        if not self._events:
            e = tk.Label(self._holder, text="Nothing scheduled in this window.\n"
                         "\u2190 Try widening the date range or clearing the filters.",
                         bg=self.palette["panel_color"], fg="#8b95a3",
                         font=(_FONT, 12), padx=18, pady=24)
            e.pack(fill="x", pady=8)
            return

        for i, ev in enumerate(self._events):
            card = tk.Frame(self._holder, bg=self.palette["panel_color"], padx=14, pady=10,
                            highlightbackground=self.palette["border_color"],
                            highlightthickness=1)
            card.pack(fill="x", pady=5)

            category = str(ev.get("category", "EVENT"))
            tag_bg, tag_fg = _cat_style(category)
            countdown = ev.get("countdown") or "T-?"
            self._accent_chip(card, countdown, bg="#5898d4", fg="#0b1020")
            self._accent_chip(card, category, bg=tag_bg, fg=tag_fg)

            self._label(card, _ts(ev, "%b %d, %Y \u00b7 %H:%M UTC"), size=9,
                        color="#6b7686")
            self._label(card, str(ev.get("title", "Untitled")), size=12, bold=True,
                        color="#edf1f7", wraplength=820)
            self._label(card, str(ev.get("info", "No details"))[:240], size=9,
                        color="#8b95a3", wraplength=820)
            self._label(card, "Details \u2192", size=9, color=self.palette["accent"])
            self._clickable(card, lambda i=i: self._open_detail(i))

    def refresh(self) -> None:
        if self._fetching:
            return
        self._fetching = True
        self._refresh_btn.configure(state="disabled")
        self._status.configure(text="Fetching space data\u2026")

        # Snapshot the filter values on the main thread — Tk vars are not
        # thread-safe and the fetch thread must not touch them.
        track = self._active_track or "all"
        after = self._parse(self._after_var.get())
        before = self._parse(self._before_var.get())
        name = (self._name_var.get() or "").strip() or None
        try:
            limit = int(self._limit_var.get() or 60)
        except (TypeError, ValueError):
            limit = 60

        def work() -> None:
            # Tk must only be touched on the main thread, so the fetch thread
            # hands the result back through a thread-safe queue; _poll drains
            # it and applies the results on the Tk event loop.
            try:
                events = self.engine.get_events(
                    track=track, after=after, before=before, name=name, limit=limit)
            except Exception as exc:  # noqa: BLE001 - surface, don't crash
                self._q.put(("error", str(exc)))
            else:
                self._q.put(("events", events))

        threading.Thread(target=work, daemon=True).start()
        self._kick_poll()

    def _kick_poll(self) -> None:
        if self._poll_job is None:
            self._poll_job = self.root.after(50, self._poll)

    def _poll(self) -> None:
        self._poll_job = None
        try:
            while True:
                kind, payload = self._q.get_nowait()
                if kind == "events":
                    self._apply_events(payload)
                else:
                    self._apply_error(payload)
        except queue.Empty:
            pass
        if self._fetching:
            self._poll_job = self.root.after(50, self._poll)

    def _apply_events(self, events: list[dict]) -> None:
        self._fetching = False
        self._refresh_btn.configure(state="normal")
        self._events = sorted(events, key=lambda e: e.get("time") or
                              datetime.min.replace(tzinfo=timezone.utc))
        if self._events:
            self._idx = min(self._idx, len(self._events) - 1)
        else:
            self._idx = 0
        self._render_cards()
        self._count.configure(text=f"Events ({len(self._events)})")
        self._status.configure(text=f"Showing {len(self._events)} event(s).")

    def _apply_error(self, message: str) -> None:
        self._fetching = False
        self._refresh_btn.configure(state="normal")
        self._status.configure(text=f"Could not load events: {message}")

    def _open_track(self, track: str) -> None:
        self._active_track = track
        info = next((c for c in self.cards if c["track"] == track), None)
        self._track_title.configure(
            text=f"{info['label']} \u2014 timeline" if info else f"{track} \u2014 timeline")
        self._track_desc.configure(text=info["desc"] if info else "")
        self._show("track")
        self.refresh()

    def _on_auto_toggle(self) -> None:
        if self._auto_var.get():
            self._start_auto()
        else:
            self._stop_auto()

    def _start_auto(self) -> None:
        self._stop_auto()
        if self._auto_var.get():
            self._auto_job = self.root.after(
                int(self._interval_var.get()) * 1000, self._auto_tick)

    def _auto_tick(self) -> None:
        self._auto_job = None
        if self._auto_var.get():
            self.refresh()
            self._auto_job = self.root.after(
                int(self._interval_var.get()) * 1000, self._auto_tick)

    def _stop_auto(self) -> None:
        if self._auto_job is not None:
            self.root.after_cancel(self._auto_job)
            self._auto_job = None

    # --------------------------------------------------------------- detail
    def _build_detail(self, container) -> None:
        page = ttk.Frame(container)
        self._detail = page

        nav = ttk.Frame(page)
        nav.pack(fill="x", pady=(2, 4))
        ttk.Button(nav, text="\u2190 Timeline", bootstyle="secondary-outline",
                   command=lambda: self._show("track")).pack(side="left")
        self._prev_btn = ttk.Button(nav, text="\u2190 Previous",
                                    bootstyle="primary-outline", command=self._prev)
        self._prev_btn.pack(side="right", padx=(0, 8))
        self._next_btn = ttk.Button(nav, text="Next \u2192",
                                    bootstyle="primary-outline", command=self._next)
        self._next_btn.pack(side="right")

        body = tk.Frame(page, bg="#070b16")
        body.pack(fill="both", expand=True, pady=10)

        self._d_title = tk.Label(body, text="", bg="#070b16", fg="#ffffff",
                                 font=(_FONT, 22, "bold"), wraplength=920,
                                 justify="left", anchor="w")
        self._d_title.pack(fill="x", pady=(6, 8))
        self._d_meta = tk.Label(body, text="", bg="#070b16", fg="#8b95a3",
                                font=(_FONT, 10), anchor="w")
        self._d_meta.pack(fill="x", pady=(0, 10))

        self._d_card = tk.Frame(body, bg=self.palette["panel_color"], padx=16, pady=12,
                                highlightbackground=self.palette["border_color"],
                                highlightthickness=1)
        self._d_card.pack(fill="both", expand=True)
        tk.Label(self._d_card, text="Details", bg=self.palette["panel_color"],
                 fg="#c3ccd8", font=(_FONT, 10, "bold")).pack(anchor="w")
        self._d_info = tk.Label(self._d_card, text="", bg=self.palette["panel_color"],
                                fg="#aab3c0", font=(_FONT, 10),
                                wraplength=910, justify="left", anchor="w")
        self._d_info.pack(fill="both", expand=True, pady=(6, 0))

    def _render_detail(self) -> None:
        if not self._events or not 0 <= self._idx < len(self._events):
            self._d_title.configure(text="No event.")
            self._d_meta.configure(text="")
            self._d_info.configure(text="Nothing to show.")
            return
        ev = self._events[self._idx]
        category = str(ev.get("category", "EVENT"))
        tag_bg, tag_fg = _cat_style(category)
        countdown = ev.get("countdown") or "T-?"
        self._d_title.configure(text=str(ev.get("title", "Untitled")))
        self._d_meta.configure(
            text=f"{_ts(ev, '%A, %B %d, %Y \u00b7 %H:%M UTC')}   "
                 f"[{category}]   {countdown}")
        self._d_info.configure(text=str(ev.get("info", "No details")))
        self._prev_btn.configure(state="normal" if self._idx > 0 else "disabled")
        self._next_btn.configure(
            state="normal" if self._idx < len(self._events) - 1 else "disabled")

    def _open_detail(self, idx: int) -> None:
        if not 0 <= idx < len(self._events):
            return
        self._idx = idx
        self._render_detail()
        self._show("detail")

    def _prev(self) -> None:
        if self._idx > 0:
            self._idx -= 1
            self._render_detail()

    def _next(self) -> None:
        if self._idx < len(self._events) - 1:
            self._idx += 1
            self._render_detail()

    # --------------------------------------------------------------- utils
    @staticmethod
    def _parse(date_str: str) -> datetime | None:
        date_str = (date_str or "").strip()
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def _on_close(self) -> None:
        self._stop_auto()
        if self._poll_job is not None:
            self.root.after_cancel(self._poll_job)
            self._poll_job = None
        self.root.destroy()


def main() -> None:
    root = ttk.Window(themename="darkly")
    SpacerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()