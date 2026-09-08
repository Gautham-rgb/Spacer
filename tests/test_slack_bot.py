"""Slack Socket Mode: ack-first ordering and background command replies."""

import time
from types import SimpleNamespace

import core.slack_bot as slack_bot


class _Req:
    type = "events_api"
    envelope_id = "env-1"

    def __init__(self, text):
        self.payload = {"event": {
            "type": "message", "channel": "C1", "user": "U1", "text": text}}


class _Client:
    def __init__(self):
        self.acks = []
        self.sent = []
        self.web_client = self  # _reply calls self.client.web_client.chat_postMessage

    def send_socket_mode_response(self, resp):
        self.acks.append(resp.envelope_id)

    def chat_postMessage(self, channel=None, text=None, blocks=None):
        self.sent.append((channel, text, blocks))


def _bot(monkeypatch):
    bot = slack_bot.SlackBot.__new__(slack_bot.SlackBot)
    bot.engine = object()
    client = _Client()
    bot.client = client
    calls = []

    def fake_dispatch(engine, cmd, **kwargs):
        calls.append((cmd, kwargs))
        return SimpleNamespace(
            slack_blocks=[{"type": "section",
                           "text": {"type": "mrkdwn", "text": "ok"}}])

    monkeypatch.setattr(slack_bot, "dispatch", fake_dispatch)
    return bot, client, calls


def test_ack_sent_before_command_is_dispatched(monkeypatch):
    bot, client, _ = _bot(monkeypatch)
    bot._on_request(client, _Req("!space version"))
    assert client.acks == ["env-1"]  # envelope acknowledged synchronously


def test_command_runs_in_background_and_replies(monkeypatch):
    bot, client, calls = _bot(monkeypatch)
    bot._on_request(client, _Req("!space version"))
    deadline = time.time() + 5
    while time.time() < deadline and not client.sent:
        time.sleep(0.02)
    assert client.sent, "background reply never arrived"
    assert len(calls) == 1
    cmd, kwargs = calls[0]
    assert cmd == "version"
    assert kwargs["context"] == {"channel": "C1", "user": "U1"}
    channel, text, blocks = client.sent[0]
    assert channel == "C1"
    assert blocks[0]["type"] == "section"


def test_non_command_messages_are_ignored(monkeypatch):
    bot, client, calls = _bot(monkeypatch)
    bot._on_request(client, _Req("hello there"))
    time.sleep(0.5)  # give any (spurious) thread a chance to run
    assert calls == [] and client.sent == [] and client.acks == ["env-1"]