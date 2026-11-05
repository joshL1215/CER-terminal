"""public read access via rls

Lets the frontend read kept articles (from active feeds) and active feeds
through the Supabase Data API as the `anon`/`authenticated` roles, limited to
public columns, and nothing else. Services connecting as the table owner
(postgres) bypass RLS and are unaffected.

Postgres only; no-op on SQLite. All checks run in SQL so `alembic upgrade --sql`
works.

Revision ID: f626cc0b0c40
Revises: 41253d736576
Create Date: 2026-11-04 18:59:35.846972

"""

from collections.abc import Sequence

from alembic import op

revision: str = "f626cc0b0c40"
down_revision: str | Sequence[str] | None = "41253d736576"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PUBLIC_ROLES = "anon, authenticated"
TABLES = ("articles", "feeds", "alembic_version")
PUBLIC_COLUMNS = {
    "articles": "id, url, title, description, published_at, category, feed_id",
    "feeds": "id, name, url, category, tags",
}
OBJECT_KINDS = ("tables", "sequences", "functions")


def _is_postgres() -> bool:
    return op.get_context().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return

    # Supabase already has these roles. Creating them elsewhere means a database
    # migrated before they exist still ends up with the grants and policies.
    op.execute(
        """
        do $$
        begin
          if not exists (select 1 from pg_roles where rolname = 'anon') then
            create role anon nologin;
          end if;
          if not exists (select 1 from pg_roles where rolname = 'authenticated') then
            create role authenticated nologin;
          end if;
        end
        $$
        """
    )

    # Supabase grants everything in `public` to these roles by default; start from nothing.
    for kind in OBJECT_KINDS:
        op.execute(
            f"alter default privileges in schema public revoke all on {kind} from {PUBLIC_ROLES}"
        )
    for table in TABLES:
        op.execute(f"revoke all on public.{table} from {PUBLIC_ROLES}")
        op.execute(f"alter table public.{table} enable row level security")
    op.execute(f"revoke all on all sequences in schema public from {PUBLIC_ROLES}")

    for table, columns in PUBLIC_COLUMNS.items():
        op.execute(f"grant select ({columns}) on public.{table} to {PUBLIC_ROLES}")

    op.execute(
        f"""
        create policy public_read_kept_articles on public.articles
        for select to {PUBLIC_ROLES}
        using (status = 'kept' and exists (select 1 from public.feeds f where f.id = feed_id))
        """
    )
    op.execute(
        f"create policy public_read_active_feeds on public.feeds "
        f"for select to {PUBLIC_ROLES} using (active)"
    )


def downgrade() -> None:
    # Leaves the roles and the revoked default privileges in place, so the public
    # roles end up with no access rather than Supabase's original grants.
    if not _is_postgres():
        return

    op.execute("drop policy if exists public_read_kept_articles on public.articles")
    op.execute("drop policy if exists public_read_active_feeds on public.feeds")
    for table in TABLES:
        op.execute(f"revoke all on public.{table} from {PUBLIC_ROLES}")
        op.execute(f"alter table public.{table} disable row level security")
