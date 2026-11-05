# Ingest

Daily RSS ingest and LLM relevance filtering for the energy terminal, run by a scheduled GitHub Actions job.

## Setup

Requires [uv](https://docs.astral.sh/uv/) (it will install Python 3.12 automatically).

```sh
cd ingest
uv sync
uv run pytest
```

## Feed registry

RSS feeds live in [`config/feeds.yaml`](config/feeds.yaml). Each feed has an `id`, `name`, `url`,
and optional metadata (`source_type`, `category`, `tags`, `active`, `llm_context`). Values under
`defaults` apply to every feed unless the feed sets its own (lists like `tags` are replaced, not
merged).

Validate the file and list feeds:

```sh
uv run python -m app.feeds            # uses config/feeds.yaml
uv run python -m app.feeds path/to/other.yaml
```

Use it in code:

```python
from app.feeds import load_feed_registry

registry = load_feed_registry()
for feed in registry.active():
    ...  # feed.url, feed.name, feed.category, feed.llm_context
```

The loader fails fast with a readable error (`feeds[1] (utility-dive).url: ...`) on unknown
fields, duplicate ids/URLs, duplicate YAML keys, bad slugs, or non-http(s) URLs.

## Database

Tables, connection setup, and migrations come from the shared
[`cer-db`](../packages/db/README.md) package (`from cer_db import Article, session_scope, ...`).
Run migrations from `packages/db/`.

This service's own queries live in `src/app/repository/`:

- `feeds.py`: `sync_feeds`, `get_feed`, `record_fetch_success`, `record_fetch_failure`
- `articles.py`: `insert_new_articles`, `get_pending_articles`, `record_classifications`,
  `record_classification_failure`

Wrap them in `session_scope(...)`. Tests use SQLite by default; set `TEST_DATABASE_URL` to a
disposable Postgres database to run them there too (its tables get dropped).
