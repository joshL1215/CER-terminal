# Backend

Python backend for the energy terminal: RSS ingest, LLM relevance filtering, and (later) the API.

## Setup

Requires [uv](https://docs.astral.sh/uv/) (it will install Python 3.12 automatically).

```sh
cd backend
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
