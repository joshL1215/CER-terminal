import pytest

from app.feeds import parse_feed_registry
from app.repository import sync_feeds

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
