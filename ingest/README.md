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

This service owns the schema (Postgres in production). Other services read the tables but don't
migrate them.

| Table      | Contents                                                                          |
| ---------- | --------------------------------------------------------------------------------- |
| `feeds`    | Mirror of `feeds.yaml` (synced each run) plus fetch state: ETag, failures, errors |
| `articles` | One row per unique article (deduped by canonical-URL hash) and its LLM decision   |

Article `status` goes `pending` → `kept` / `rejected`, or `failed` after repeated LLM errors.

Set `DATABASE_URL` (a plain `postgresql://` URL from Supabase works), then:

```sh
uv run alembic upgrade head                          # create/upgrade tables
uv run alembic revision --autogenerate -m "message"  # after editing src/app/db/models.py
```

On Supabase, use the **session pooler** connection string for GitHub Actions: the direct
connection is IPv6-only on the free plan and Actions runners don't support IPv6.

Queries the ingest job uses live in `app/db/repository.py` (`sync_feeds`, `insert_new_articles`,
`get_pending_articles`, `record_classifications`, ...). Wrap them in `session_scope(...)`.

Tests use SQLite by default. To also run them against a disposable Postgres database (its tables
get dropped):

```sh
TEST_DATABASE_URL=postgresql://... uv run pytest
```
