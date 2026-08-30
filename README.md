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

Needs Python 3.10+ and pip.

```bash
pip install -e .
```

That drops four commands on your machine:

- `spacer` — the terminal CLI
- `spacer-gui` — the desktop window
- `spacer-web` — just the web page
- `spacer-serve` — web page + both bots in one process (good for a server)

(Some day I might put it on PyPI. Today is not that day. The `-e` install is fine.)

## Quickstart

From the terminal:

```bash
spacer                                       # everything, listed
spacer probe_launch list --limit 10
spacer all list --after 2026-01-01 --before 2026-12-31 --name mars
spacer space_weather notify                  # ping me about weather soon
```

Flags: `--after` / `--before` (YYYY-MM-DD), `--name`, `--limit`, `--webhook`.
Also `--version`, `--check-update`, `--slack`, `--discord`.

For just the desktop window: `spacer-gui`. For just the web page: `spacer-web`.

## Talking to it in Slack and Discord

Both bots listen in any channel they can see:

- `!space list [track]` — events. Track is `all`, `space_weather`,
  `space_events`, `probe_launch`, or `probe_events`.
- `!space weather` — just space weather.
- `!space launches` — just launches.
- `!space version` — which build is running.
- `!space help` — the above, in chat.

Start them with:

```bash
spacer --slack
spacer --discord
```

They read tokens from `.env`. Slack wants `SLACK_BOT_TOK` and
`SLACK_APP_TOK`; Discord wants `DISCORD_BOT_TOK`. (`.env` is gitignored — set
them locally or as environment variables on your server.) The web page also has
an optional "Ask Groq" box at the bottom.

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
There's a `Procfile` (`web: python app.py`) for platforms like Hack Club Nest
that boot from that, and a `Dockerfile` too.

On Nest: connect the repo, set the tokens as secrets, and it'll serve the page
and start whichever bots have tokens. You can also just clone it,
`pip install -e .`, export the tokens, and run `python app.py` inside a `tmux`
session so it survives you logging off.

Binding to `0.0.0.0:$PORT` is necessary but not enough to make the site public
— Nest is a plain Linux VPS, so you also need a reverse proxy. The included
`Caddyfile` proxies the app (which listens on `localhost:8080`) and passes
through NiceGUI's websocket for the live UI:

```bash
docker compose up -d web      # maps 8080 on the host
caddy run --config Caddyfile  # or: put Caddy in front of the container
```

Without the proxy (or a port forward), the page only listens inside the
container and won't be reachable from the internet.

## Docker

One image, three services:

```bash
docker compose up --build
```

That starts `web` (page on port 8080), `slack`, and `discord`. The `de421.bsp`
astronomy file is baked into the image; your `.env` is not — compose passes it
in at runtime.

Run just one: `docker compose up --build web`.

## Configuration

| Variable | What it's for |
| --- | --- |
| `SLACK_BOT_TOK`, `SLACK_APP_TOK` | Slack app tokens (Socket Mode). |
| `DISCORD_BOT_TOK` | Discord bot token. |
| `API_KEY` | thespacedevs key (falls back to `DEMO_KEY`). |
| `GROQ_API_KEY` | optional; powers `!groq` and the web chat box. |
| `PORT` | port the web server binds (default 8080). |

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
