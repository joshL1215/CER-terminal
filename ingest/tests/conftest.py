import json

import pytest
from cer_db import make_session_factory

from app.classify import Provider
from app.feeds import parse_feed_registry
from app.repository import sync_feeds
from app.rules import parse_rules

# Shared database fixtures (database_url, engine, session) from the cer-db package.
pytest_plugins = ["cer_db.testing"]


REGISTRY_YAML = """
version: 1
feeds:
  - id: alpha
    name: Alpha News
    url: https://alpha.example.com/rss
    category: Grid
    tags: [utilities]
    llm_context: Alpha context.
  - id: beta
    name: Beta
    url: https://beta.example.com/rss
    active: false
"""


@pytest.fixture
def registry():
    return parse_feed_registry(REGISTRY_YAML)


@pytest.fixture
def feeds(session, registry):
    """Sync REGISTRY_YAML's feeds (alpha active, beta inactive) into the DB."""
    sync_feeds(session, registry)
    session.commit()


@pytest.fixture
def factory(engine):
    return make_session_factory(engine)


@pytest.fixture
def rules():
    return parse_rules(
        """
        version: test-v1
        categories: [grid, policy, other]
        keep: [Grid news]
        reject: [Celebrity news]
        keyword_reject: [giveaway]
        """
    )


@pytest.fixture
def providers():
    return [
        Provider("https://primary.example.com/v1", "model-a", "key-a"),
        Provider("https://fallback.example.com/v1", "model-b", "key-b"),
    ]


class FakeChatClient:
    """Stands in for an LLM: `respond(provider, ids)` returns the reply text or raises."""

    def __init__(self, respond):
        self.respond = respond
        self.calls = []

    def complete(self, provider, messages):
        payload = json.loads(messages[1]["content"].split("\n", 1)[1])
        ids = [article["id"] for article in payload]
        self.calls.append((provider, ids))
        return self.respond(provider, ids)


def answer(ids, keep=True, category="grid"):
    """An LLM reply deciding every id the same way."""
    results = [{"id": i, "keep": keep, "category": category, "reason": "ok"} for i in ids]
    return json.dumps({"results": results})


@pytest.fixture
def fake_llm():
    return FakeChatClient


@pytest.fixture
def llm_answer():
    return answer
