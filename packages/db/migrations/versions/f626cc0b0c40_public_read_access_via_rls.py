"""public read access via rls

Lets the frontend read kept articles and active feeds through the Supabase
Data API as the `anon`/`authenticated` roles, and nothing else. Services that
connect as the table owner (postgres) bypass RLS and are unaffected.

Postgres only. Grants and policies are skipped where the Supabase roles don't
exist (plain Postgres, e.g. local or test databases); RLS is still enabled.

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

TABLES = ("articles", "feeds")
PUBLIC_ROLES = "anon, authenticated"


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _supabase_roles_exist() -> bool:
    count = op.get_bind().exec_driver_sql(
        "select count(*) from pg_roles where rolname in ('anon', 'authenticated')"
    )
    return count.scalar() == 2


def upgrade() -> None:
    if not _is_postgres():
        return

    for table in TABLES:
        op.execute(f"alter table public.{table} enable row level security")

    if not _supabase_roles_exist():
        return

    for table in TABLES:
        op.execute(f"revoke all on public.{table} from {PUBLIC_ROLES}")
        op.execute(f"grant select on public.{table} to {PUBLIC_ROLES}")

    op.execute(
        f"create policy public_read_kept_articles on public.articles "
        f"for select to {PUBLIC_ROLES} using (status = 'kept')"
    )
    op.execute(
        f"create policy public_read_active_feeds on public.feeds "
        f"for select to {PUBLIC_ROLES} using (active)"
    )


def downgrade() -> None:
    if not _is_postgres():
        return

    op.execute("drop policy if exists public_read_kept_articles on public.articles")
    op.execute("drop policy if exists public_read_active_feeds on public.feeds")

    if _supabase_roles_exist():
        for table in TABLES:
            op.execute(f"revoke select on public.{table} from {PUBLIC_ROLES}")

    for table in TABLES:
        op.execute(f"alter table public.{table} disable row level security")
