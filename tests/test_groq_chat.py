"""Groq chat: conversation memory, reset, and key cap."""

import pytest
from types import SimpleNamespace

import core.groq_chat as mod


@pytest.fixture(autouse=True)
def _reset_state():
    mod._conversations.clear()
    yield
    mod._conversations.clear()
    mod._client = None


class _Completions:
    def __init__(self, client):
        self.client = client

    def create(self, **kwargs):
        self.client.calls.append(kwargs)
        user_content = kwargs["messages"][-1]["content"]
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=f"ans:{user_content}"))])


class _Chat:
    def __init__(self, client):
        self.completions = _Completions(client)


class _FakeClient:
    def __init__(self):
        self.calls = []
        self.chat = _Chat(self)


def _install_fake(monkeypatch):
    client = _FakeClient()
    monkeypatch.setattr(mod, "_client", client)
    return client


def test_single_turn_does_not_store_without_key(monkeypatch):
    client = _install_fake(monkeypatch)
    assert mod.groq_chat("hi") == "ans:hi"
    messages = client.calls[0]["messages"]
    assert [m["role"] for m in messages] == ["system", "user"]


def test_history_included_on_follow_up(monkeypatch):
    client = _install_fake(monkeypatch)
    mod.groq_chat("what is the next launch?", key="U@C")
    mod.groq_chat("and its booster?", key="U@C")
    messages = client.calls[1]["messages"]
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert messages[1] == {"role": "user", "content": "what is the next launch?"}
    assert messages[2] == {"role": "assistant", "content": "ans:what is the next launch?"}
    assert messages[3]["content"] == "and its booster?"


def test_conversation_length_and_clear(monkeypatch):
    _install_fake(monkeypatch)
    mod.groq_chat("one", key="k")
    assert mod.conversation_length("k") == 1
    mod.clear_conversation("k")
    assert mod.conversation_length("k") == 0


def test_reset_flag_forgets_history(monkeypatch):
    client = _install_fake(monkeypatch)
    mod.groq_chat("first", key="k")
    mod.groq_chat("second", key="k", reset=True)
    messages = client.calls[1]["messages"]
    assert [m["role"] for m in messages] == ["system", "user"]
    assert messages[-1]["content"] == "second"


def test_memory_capped_at_max_turns(monkeypatch):
    client = _install_fake(monkeypatch)
    for i in range(10):
        mod.groq_chat(f"q{i}", key="k")
    messages = client.calls[-1]["messages"]
    # system + last (2 * _MAX_TURNS) stored messages + the new user turn
    assert len(messages) == 1 + mod._MAX_TURNS * 2 + 1
    assert messages[-1]["content"] == "q9"


def test_key_count_is_bounded(monkeypatch):
    _install_fake(monkeypatch)
    for i in range(105):
        mod.groq_chat(f"q{i}", key=f"k{i}")
    assert len(mod._conversations) == mod._MAX_KEYS
    mod.groq_chat("one more", key="last")
    assert len(mod._conversations) <= mod._MAX_KEYS
    assert "k0" not in mod._conversations  # oldest evicted
    assert "last" in mod._conversations


def test_eviction_is_least_recently_used(monkeypatch):
    _install_fake(monkeypatch)
    for i in range(105):  # cap keeps k5..k104 (k0..k4 already evicted along the way)
        mod.groq_chat(f"q{i}", key=f"k{i}")
    assert len(mod._conversations) == mod._MAX_KEYS
    mod.groq_chat("revisit an old key", key="k50")  # now the MRU key
    mod.groq_chat("overflow", key="new")            # forces one eviction
    assert len(mod._conversations) == mod._MAX_KEYS
    assert "k50" in mod._conversations   # recently-used key survives
    assert "new" in mod._conversations   # newest key survives
    assert "k5" not in mod._conversations  # oldest survivor was the LRU -> evicted
    assert "k6" in mod._conversations      # 2nd-oldest untouched, kept


def test_blank_prompt_returns_hint():
    assert mod.groq_chat("   ").startswith("Ask me something")


def test_missing_client_reports_config(monkeypatch):
    monkeypatch.setattr(mod, "_client", None)
    assert "GROQ_API_KEY" in mod.groq_chat("hi")