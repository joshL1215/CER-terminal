# cer-db

Shared database layer for the energy terminal services: table definitions, connection setup, and
the schema's migrations. Every service that uses the database depends on this package, so the
schema is defined in exactly one place.

| Table      | Contents                                                                          |
| ---------- | --------------------------------------------------------------------------------- |
| `feeds`    | Mirror of the ingest service's `feeds.yaml` plus fetch state: ETag, failures      |
| `articles` | One row per unique article (deduped by canonical-URL hash) and its LLM decision   |

Article `status` goes `pending` → `kept` / `rejected`, or `failed` after repeated LLM errors.

## Using it from a service

In the service's `pyproject.toml` (or run `uv add --editable ../packages/db`):

```toml
dependencies = ["cer-db"]

[tool.uv.sources]
cer-db = { path = "../packages/db", editable = true }
```

```python
from cer_db import Article, ArticleStatus, make_engine, make_session_factory, session_scope

factory = make_session_factory(make_engine())  # reads DATABASE_URL
with session_scope(factory) as session:
    ...
```

Service-specific queries stay in the service (e.g. `ingest/src/app/repository/`).

For tests, add `pytest_plugins = ["cer_db.testing"]` to the service's `conftest.py` to get
`database_url`, `engine`, and `session` fixtures.

## Migrations

Set `DATABASE_URL` (a plain `postgresql://` URL from Supabase works), then from this folder:

```sh
uv sync
uv run alembic upgrade head                          # create/upgrade tables
uv run alembic revision --autogenerate -m "message"  # after editing src/cer_db/models/
```

On Supabase, use the **session pooler** connection string for GitHub Actions: the direct
connection is IPv6-only on the free plan and Actions runners don't support IPv6.

## Public read access (Supabase Data API)

The frontend reads through the Supabase Data API with the public `anon` key. A migration limits
the `anon` and `authenticated` roles to reading:

| Table      | Rows                               | Columns                                                         |
| ---------- | ---------------------------------- | --------------------------------------------------------------- |
| `articles` | `status = 'kept'` from active feeds | `id, url, title, description, published_at, category, feed_id` |
| `feeds`    | `active = true`                    | `id, name, url, category, tags`                                 |

Everything else is denied: other rows and columns, all writes, `alembic_version`, sequences, and
any table created later (the migration also revokes Supabase's default grants in `public`, so
new tables must be exposed by a migration on purpose). Because access is per column, frontend
queries must list columns; `select=*` is rejected. Services connecting as `postgres` (the table
owner) bypass RLS.

**Rollout order matters.** Before the migration, Supabase's default grants may leave the tables
fully open to the `anon` key. So:

1. Run `uv run alembic upgrade head` first.
2. Then, in **Integrations → Data API**, turn the Data API on and keep "Automatically expose new
   tables" off.

On plain Postgres (local, tests), the migration creates `anon`/`authenticated` as login-less roles
so the result is the same everywhere.

## Tests

```sh
uv run pytest                                   # SQLite
TEST_DATABASE_URL=postgresql://... uv run pytest # also Postgres (its tables get dropped)
```

`test_migrations` fails if a model changes without a matching migration.
