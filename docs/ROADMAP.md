# Spacer — Roadmap: GUI + Web

Last updated: 2026-08-21
Status: planning

## Current architecture (what we have)

- `src/engine.py` — `SpaceEngine` gathers, filters, and acts on events.
- `src/events/` — `SpaceWeatherEvent`, `ProbeEvent`, `AstronomyEvent`, each with `fetch_timeline_data()`.
- `src/core/` — `APIClient`, `Notifier` (desktop + webhook), `TimelineFormatter` (CLI + markdown), `EventEnricher` (Wiki + Groq).
- `src/CLI_bot/CLI.py` — argparse entry point (`spacer` script).

The engine already returns a clean list of dicts (`time`, `category`, `title`, `info`).
Both new UIs should consume that list, not reimplement fetching.

## Guiding principle

Keep the engine headless and UI-agnostic. Add a single `SpaceEngine.get_events(...)`
method that returns the filtered list. CLI, GUI, and web all call it. No logic
duplication across front-ends.

---

## Phase 0 — Engine refactor (foundation)

Goal: expose data without forcing print/notify side effects.

- [ ] Add `SpaceEngine.get_events(track, after, before, name, limit) -> list[dict]`
      that does gather + filter only (no notify, no render).
- [ ] Keep `run(...)` working by having it call `get_events()` then render/notify.
- [ ] Make `TimelineFormatter` importable without side effects (already is).
- [ ] Add a small `Event` dataclass / TypedDict so UIs have a stable shape.

Outcome: one source of truth for "what events exist right now".

## Phase 1 — Desktop GUI

Goal: a windowed app that shows the live timeline and lets you filter.

Candidate stacks (pick one before building):
- `textual` — TUI, reuses rich styling, tiny deps. Feels like the CLI in a terminal.
- `ttkbootstrap` — real native window, lightweight, stdlib-ish. Normal desktop app.
- `nicegui` — browser-engine UI in a desktop window; shares code with the web app
  (see Phase 2) since NiceGUI is web-based. Best if you want GUI + web to look identical.

Decision: if you want the GUI and web to share one codebase, use `nicegui`
for both. If you want a pure terminal UI, use `textual`. If you want a classic
native window, use `ttkbootstrap`.

- [ ] `src/gui/app.py` — main view with:
      - [ ] Track selector (all / space_weather / space_events / probe_launch / probe_events)
      - [ ] Date range + name filter + limit inputs
      - [ ] "Refresh" button -> calls `SpaceEngine.get_events(...)`
      - [ ] Event list / timeline view (category tag, countdown, title, info)
- [ ] Wire desktop notifications via existing `Notifier`.
- [ ] Add `spacer-gui` script entry in `pyproject.toml`.
- [ ] Package the GUI (PyInstaller / briefcase) for a double-click app.

## Phase 2 — Web app (Hugging Face Spaces)

Goal: a hosted dashboard anyone can open in a browser, deployed on
Hugging Face Spaces so there is zero self-hosting.

Recommended approach: **Gradio** Space (native to HF, no Docker, fastest to
ship). The GUI/CLI already reuse `get_events`; here we wrap the same engine in
a Gradio app. Alternative: Docker Space running the FastAPI + static frontend
from the original plan, if you want a custom SPA instead of Gradio widgets.

- [ ] `src/web/app.py` — Gradio app built on `SpaceEngine.get_events(...)`:
      - [ ] Track selector (all / space_weather / space_events / probe_launch / probe_events)
      - [ ] Date-range, name, and limit inputs
      - [ ] Live timeline output (category tag, countdown, title, info)
      - [ ] "Refresh" button -> re-calls `get_events(...)`
- [ ] `requirements.txt` (or keep `pyproject.toml`) listing `gradio` + existing deps.
- [ ] `README.md` + `app.py` at repo root for the Space (HF convention).
- [ ] Optional: keep a `FastAPI` Docker Space branch for a custom SPA later.
- [ ] Document the Space URL once deployed.

## Phase 3 — Shared polish

- [ ] Unified config (API keys, refresh interval) via `.env` / settings panel.
      On HF Spaces, use the Space's Secrets tab for `API_KEY` / `GROQ_API_KEY`.
- [ ] Caching layer so the web/GUI don't hammer NOAA + thespacedevs on every refresh.
- [ ] Consistent styling across CLI (rich), GUI, and web.
- [ ] README updated with all three run modes + the Hugging Face Space link.
- [ ] Ship to PyPI with `spacer`, `spacer-gui` commands (web lives on the Space).

## Open questions

- GUI framework: `textual` (TUI), `ttkbootstrap` (native window), or `nicegui`
  (web-based, can share code with the HF web app)? Recommend `nicegui` if you
  want GUI + web to be one codebase.
- Web frontend: Gradio (recommended, fastest on HF) vs Docker Space + FastAPI SPA?
- Hosting: web is set for Hugging Face Spaces — confirm Space name / visibility.
