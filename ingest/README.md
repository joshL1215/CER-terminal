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

## Keyword relevance filter

The local filter checks article titles and descriptions against
[`config/filter_rules.yaml`](config/filter_rules.yaml). It needs no database, API key, or network
access and does not change article database statuses.

```python
from app.filtering.rules import filter_article, load_filter_rules

rules = load_filter_rules()  # load once; optionally pass a custom YAML path
result = filter_article(
    title="Coal consumption falls as solar generation increases",
    description=None,
    rules=rules,
)
print(result.decision.value)  # relevant
print(result.topics)          # ('coal', 'renewables')
print(result.matched_keywords)  # ('coal', 'solar')
```

Configure literal keywords under `topics` and optional unwanted phrases under `exclusions`.
Exclusion matches are reported as evidence only and do not change the decision. Matching ignores
case, HTML markup, whitespace, and punctuation, and uses whole words/phrases (`oil` does not match
`soil`). Add plurals and synonyms explicitly. Phrases must occur within the title or description,
not across both fields. Invalid rules and duplicate YAML keys raise `FilterConfigError`.

| Matches | Decision | Intended pipeline action |
| --- | --- | --- |
| Any topic keyword in the title or description | `relevant` | Accept without AI relevance review |
| No topic keywords | `needs_review` | Send to AI relevance filtering |

Results include matched topics, keywords, exclusions, and an explanation. Keyword matches bypass
AI relevance review; unmatched articles go to AI so useful articles with unfamiliar wording can
still be found. Matches are heuristics, so audit accepted articles and tune the keywords as needed.
Bypassing AI relevance review does not generate an AI summary or verify factual claims.
This filter is not yet wired into an ingestion pipeline.

Run its sample-based tests locally:

```sh
uv run pytest tests/test_filter_rules.py
```

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
