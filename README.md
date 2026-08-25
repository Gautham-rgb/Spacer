# Spacer

A CLI tool / Slack / Discord bot that lets space enthusiasts track upcoming
space events — solar flares, CMEs, planetary conjunctions, and rocket launches.

Spacer has **one headless engine** (`SpaceEngine.get_events`) that every
front-end consumes. No fetching logic is duplicated across the CLI, chat bots,
desktop GUI, or web app.

## Features

- **CLI** — `spacer [track] [list|notify]` with date-range, name, and limit filters.
- **Slack bot** — Socket Mode app, replies to `!space list|weather|launches|version|help`
  with Block Kit messages (needs `SLACK_BOT_TOK` + `SLACK_APP_TOK`).
- **Discord bot** — discord.py app, same `!space` commands, replies with Embeds
  (needs `DISCORD_BOT_TOK`).
- **Desktop GUI** — native window via `ttkbootstrap` (`spacer-gui`).
- **Web app** — NiceGUI dashboard, deployable on Hack Club Nest / Hugging Face
  Spaces (`spacer-web`, or run the repo-root `app.py`).
- **Version + update check** — single-source `__version__`
  (`src/version.py`), shown in the CLI banner and `--version`, with
  `spacer --check-update` querying PyPI.

## Install

```bash
pip install -e .        # or: pip install -r requirements.txt
```

Optional chat-bot extras: `slack_sdk` and `discord.py` are already listed; set
the tokens in your environment (see `.env`).

## Usage

```bash
# CLI
spacer all list --limit 10
spacer space_weather notify
spacer --version
spacer --check-update

# Chat bots (interactive, listen for "!space ...")
spacer --slack
spacer --discord

# Desktop GUI
spacer-gui

# Web (Hack Club Nest / HF Spaces)
spacer-web

# Web + chat bots on one server (Nest/HF entry point)
spacer-serve
```

## Running on a server (Hack Club Nest)

The web app and the chat bots can run on the **same** server process. The web
app owns the main thread (bound to ``0.0.0.0:$PORT``); any bot whose tokens
are present in the environment starts automatically in a background thread:

- `spacer-serve` (or the repo-root `app.py`) runs web + Slack + Discord together.
- A `Procfile` is included: `web: python app.py`, which is what Nest boots.
- Set `SLACK_BOT_TOK` + `SLACK_APP_TOK` and/or `DISCORD_BOT_TOK`; missing tokens
  simply mean that bot doesn't start — the web server keeps running.
- Desktop notifications (plyer) are skipped automatically on headless servers.

## Configuration

Set these in `.env` (the repo already includes example Slack tokens):

- `SLACK_BOT_TOK`, `SLACK_APP_TOK` — Slack Socket Mode app.
- `DISCORD_BOT_TOK` — Discord bot token.
- `API_KEY` — thespacedevs API key (defaults to `DEMO_KEY`).
- `GROQ_API_KEY` — optional, used to enrich launch descriptions.

## Project layout

- `src/engine.py` — `SpaceEngine`: gather + filter, the single source of truth.
- `src/events/` — `SpaceWeatherEvent`, `ProbeEvent`, `AstronomyEvent`.
- `src/core/` — `APIClient`, `Notifier`, `TimelineFormatter`, `EventEnricher`,
  `EventCache`, `bot_base` (shared chat logic), `slack_bot`, `discord_bot`,
  `updates` (PyPI check).
- `src/CLI_bot/CLI.py` — argparse entry point (`spacer`).
- `src/gui/app.py` — ttkbootstrap desktop window (`spacer-gui`).
- `src/web/app.py` — NiceGUI web app (`spacer-web`); `app.py` at root boots it.

## Roadmap status

- [x] Phase 0 — engine refactor + `Event` model + stable `get_events`.
- [x] Phase 1 — desktop GUI (ttkbootstrap).
- [x] Phase 2 — web app (NiceGUI, Nest/HF ready).
- [x] Phase 3 — caching, shared config, Slack + Discord, version/update check.
