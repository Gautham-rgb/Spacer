# Spacer

Spacer pulls together upcoming space stuff — solar weather, rocket launches,
and planetary events — and lets you look at it from a few different places:
the terminal, Slack, Discord, a desktop window, or a web page.

There's one core function, `SpaceEngine.get_events(...)`, that does all the
fetching and filtering. Everything else (the CLI, the bots, the GUI, the web
page) just calls it, so the actual logic only lives in one spot.

## Install

```
pip install -e .
```

That gives you the `spacer`, `spacer-gui`, `spacer-web`, and `spacer-serve`
commands.

## Using it from the terminal

```
spacer                                  # everything, listed
spacer space_weather notify             # ping me about weather in the next hour
spacer probe_launch list --limit 10
spacer all list --after 2026-01-01 --before 2026-12-31 --name mars
```

Flags you can use: `--after` and `--before` (YYYY-MM-DD), `--name`, `--limit`,
`--webhook`. Also `--version`, `--check-update`, `--slack`, `--discord`.

The `--slack` and `--discord` flags start the chat bots (see below). For just
the desktop window run `spacer-gui`; for just the web page run `spacer-web`.

## Slack and Discord

Both bots listen for `!space` commands in whatever channel they can see:

- `!space list [track]` — events. The track is `all`, `space_weather`,
  `space_events`, `probe_launch`, or `probe_events`.
- `!space weather` — just space weather.
- `!space launches` — just launches.
- `!space version` — which build is running.
- `!space help` — shows the above.

Run them with:

```
spacer --slack
spacer --discord
```

They read tokens from `.env`: Slack wants `SLACK_BOT_TOK` and
`SLACK_APP_TOK`, Discord wants `DISCORD_BOT_TOK`. The `.env` file is
gitignored, so set those locally or as environment variables on your server.

Slack side of things: turn on Socket Mode in your app, give the bot the
`chat:write` and `*-history` scopes, and subscribe to the `message.*` events.
Discord side: make a bot, switch on the Message Content intent, and invite it
with the Send Messages permission.

## Running it on a server

If you want the web page and the bots all at once, `spacer-serve` runs them in
a single process — the web app takes the main thread and the bots run in the
background. There's a `Procfile` (`web: python app.py`) for platforms like
Hack Club Nest that boot from that file. On Nest, set the tokens as secrets
and it'll serve the page and start whichever bots have tokens.

## Docker

You can also run each mode in its own container. One image, three services:

```
docker compose up --build
```

That starts `web` (the page on port 8080), `slack`, and `discord`. The
`de421.bsp` file (the astronomy data) is baked into the image; your `.env` is
not — compose passes it in at runtime instead.

To run just one of them: `docker compose up --build web`, and so on.

## Configuration

- `SLACK_BOT_TOK`, `SLACK_APP_TOK` — Slack app tokens (Socket Mode).
- `DISCORD_BOT_TOK` — Discord bot token.
- `API_KEY` — thespacedevs key (falls back to `DEMO_KEY` if unset).
- `GROQ_API_KEY` — optional, used to fill in launch descriptions.

## How the code is laid out

- `src/engine.py` — `SpaceEngine`, the core. Gather + filter, returns events.
- `src/events/` — where each kind of event is fetched (weather, launches,
  astronomy).
- `src/core/` — the supporting pieces: API client, notifier, formatter,
  enricher, cache, the chat-bot shared logic (`bot_base`), the Slack/Discord
  adapters, and the version/update check.
- `src/CLI_bot/CLI.py` — the terminal entry point.
- `src/gui/app.py` — the desktop window (`spacer-gui`).
- `src/web/app.py` — the web page (`spacer-web`); the `app.py` at the repo
  root boots it for hosting.

That's the whole thing.
