# Spacer

Spacer is a little tool that grabs upcoming space stuff — solar weather, rocket
launches, and planetary / astronomy events — and shows it to you wherever you
happen to be looking: the terminal, Slack, Discord, a desktop window, or a web
page.

The whole thing is built around one function, `SpaceEngine.get_events(...)`.
Every front-end (CLI, bots, GUI, web) just calls that, so all the fetching and
filtering lives in exactly one place. No copy-paste across five files — I
learned that lesson the hard way.

## The Reason I Made This

I kept missing rocket launches. Not the big famous ones — those are everywhere —
but the weird little ones, and the solar storms that make the radio go funny,
and the alignment windows where 2planets have a cool oppposition in conjunction. The
launch sites are a chore to dig through, and the space-weather feeds are
written for people with degrees I don't have. So I built the thing I wanted:
one place that just tells me what's coming up, in plain language, that I can
also boss around from Slack when I'm supposed to be doing something else.

(There's also a Groq-powered `!groq` command now, because sometimes you just
want to ask "what the heck is a coronal mass ejection" without opening a new
tab. More on that below.)

## Installation

Needs Python 3.11+ and pip.

```bash
pip install -e .
```

That drops four commands on your machine:

- `spacer` — the terminal CLI (events + management subcommands)
- `spacer-gui` — the desktop window
- `spacer-web` — just the web page
- `spacer-serve` — web page + both bots in one process (good for a server)

## Quickstart

From the terminal:

```bash
spacer events list                              # last day -> next two weeks, all tracks
spacer events list probe_launch --limit 10
spacer events list all --after 2026-01-01 --before 2026-12-31 --name mars --format json
spacer events show probe_launch 3               # full details for event #3
spacer notify space_weather                     # ping you about weather in the next hour
```

The CLI is split into command groups:

- `spacer events list|show` — timelines and single-event details (flags:
  `--after` / `--before` in `YYYY-MM-DD`, `--name`, `-l/--limit`,
  `-F/--format cli|md|json`)
- `spacer tracks` — the configured tracks
- `spacer config` — effective settings (and which tokens are set)
- `spacer health` — checks every upstream API, one line at a time
- `spacer notify [track]` — desktop notification for events in the next hour
- `spacer cache clear|stats` — inspect or delete the fetch cache
- `spacer update` / `spacer -V` — release check / version

For just the desktop window: `spacer-gui`. For just the web page: `spacer-web`.

## Talking to it in Slack and Discord

Both bots listen in any channel they can see:

- `!space list [track] [--limit N] [--name text]` — events. Track is `all`,
  `space_weather`, `space_events`, `probe_launch`, or `probe_events`.
- `!space weather` — just space weather.
- `!space launches` — just launches.
- `!space update` — check for a newer release.
- `!space version` — which build is running.
- `!space help` — the above, in chat.

Start them with:

```bash
spacer --slack
spacer --discord
```

They read tokens from `.env`. Slack wants `SLACK_BOT_TOK` and
`SLACK_APP_TOK`; Discord wants `DISCORD_BOT_TOK`. (`.env` is gitignored — set
them locally or as environment variables on your server.)

**Groq makes events verbose.** There is no `!groq` command — instead, Groq is
used behind the scenes to enrich event descriptions (e.g. launch missions that
lack a summary get a concise AI-written blurb pulled from Wikipedia + Groq), so
the `!space` / `/space` listings and the web cards come back with richer detail
automatically. Set `GROQ_API_KEY` to enable it; without a key, events fall back
to their plain descriptions.

Slack setup: turn on Socket Mode, give the bot `chat:write` and the
`*-history` scopes, subscribe to `message.*` events. Discord setup: make a bot,
invite it with Send Messages. On Discord, the `!space` prefix command requires
the **Message Content** privileged intent in the Discord Developer Portal —
flip it on, or use the `/space` slash command instead.

## Running it on a server (Nest, etc.)

If you want the web page and the bots together, `spacer-serve` runs them in one
process — the web app takes the main thread, the bots run in the background.

On Nest: clone the repo, set the tokens as secrets in the repo-root `.env`, and
bring it up with Docker Compose from the `deploy/` folder (see below). You can
also just clone it, `pip install -e .`, export the tokens, and run
`python app.py` inside a `tmux` session so it survives you logging off.

The repo is laid out as:

```
spacer_bot/
├── app.py            # Nest entrypoint (must stay at repo root)
├── pyproject.toml    # packaging + dependencies (single source of truth)
├── de421.bsp         # bundled JPL ephemeris (used by the astronomy tracker)
├── .env / .gitignore / .dockerignore / LICENSE / README.md
├── src/              # all the Python code (engine, core/, events/, web/, ...)
├── deploy/           # Dockerfile, docker-compose.yml (deps come from pyproject.toml)
└── docs/             # ROADMAP.md
```

**Nest serves the site on port 80.** In your Nest Domains panel the target port
is `80`, and any custom domain must be pointed at `systemic-speed.hackclub.app`.
Nest terminates HTTPS, so we do **not** run our own reverse proxy. The `web`
service binds the app to port 80 inside the container:

```bash
cd deploy
docker compose up -d web slack discord   # website + both bots
# or just: docker compose up -d web       # website only
```

Then open your site at `https://systemic-speed.hackclub.app` (or whatever custom
domain you attached in the Nest panel). If the page loads locally on 8080 but
not through the domain, double-check that a domain is configured in the Nest
panel and that it's pointed at `systemic-speed.hackclub.app`.

## Docker

One image, three services:

```bash
cd deploy && docker compose up --build
```

That starts `web` (page on port 80), `slack`, and `discord`. The `de421.bsp`
astronomy file is baked into the image; your `.env` is not — compose passes it
in at runtime.

Run just one: `cd deploy && docker compose up --build web`.

## Configuration

| Variable | What it's for |
| --- | --- |
| `SLACK_BOT_TOK`, `SLACK_APP_TOK` | Slack app tokens (Socket Mode). |
| `DISCORD_BOT_TOK` | Discord bot token. |
| `API_KEY` | thespacedevs key (falls back to `DEMO_KEY`). |
| `GROQ_API_KEY` | optional; powers event enrichment and the web chat box. |
| `PORT` | port the web server binds (default 8080; Nest uses 80). |

## How the code is laid out

- `src/engine.py` — `SpaceEngine`, the core. Gather + filter, returns events.
- `src/events/` — where each kind of event is fetched (weather, launches, astronomy).
- `src/core/` — the supporting bits: API client, notifier, formatter, the
  Groq wrapper, the chat-bot shared logic (`bot_base`), the Slack/Discord
  adapters, the version/update check.
- `src/CLI_bot/CLI.py` — the terminal entry point.
- `src/gui/app.py` — the desktop window (`spacer-gui`).
- `src/web/app.py` — the web page (`spacer-web`); the `app.py` at the repo
  root boots it for hosting.

## Tips

- **Use `spacer-serve` on a server.** It's the least fiddly way to get web + bots up.
- **The `!groq` command is separate from `!space`.** It doesn't need a track or
  a subcommand — just ask it stuff.
- **`--check-update`** tells you if a newer build exists (it checks PyPI, but
  honestly just `git pull` is faster).
- **Stuck?** `spacer --help` and the bots' `!space help` cover most of it.
- **Use it via code:** `from engine import SpaceEngine` and call
  `SpaceEngine().get_events(...)` directly. It's just a function.

## Credits

Made by Gautham, and way too much coffee.

The space data comes from [The Space Devs](https://thespacedevs.com/) and NOAA;
the astronomy is computed locally from JPL's `de421.bsp` via Skyfield. Groq
powers the chat. None of this would exist without those.

## License

GNU GPLv3 — see the `LICENSE` file. Go forth and look at space.
