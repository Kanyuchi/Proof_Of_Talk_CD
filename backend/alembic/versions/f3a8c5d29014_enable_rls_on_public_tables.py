"""enable_rls_on_public_tables

Revision ID: f3a8c5d29014
Revises: e1f2d4a36789
Create Date: 2026-04-29 19:55:00.000000

Closes Supabase advisor warning `rls_disabled_in_public` on the matchmaker
DB. Enables RLS on the nine matchmaker-owned tables that had it off; no
policies are added because nothing legitimate uses the `anon` role —
the FastAPI backend connects as the `postgres` table owner (bypasses RLS)
and the frontend goes through the backend, never directly to Supabase.

Tables left alone (RLS already on, with deliberate anon policies — these
are 1000 Minds shared tables, not ours): cold_outreach, nominations,
speakers.

`alembic_version` is Alembic's internal bookkeeping table. Owners still
have full access for migrations; only anon is locked out.

Reversibility: downgrade disables RLS again (rolls the warning back).
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'f3a8c5d29014'
down_revision: Union[str, None] = 'e1f2d4a36789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables that are matchmaker-owned and had RLS off as of 2026-04-29.
# Explicit list, not a DO loop, so 1000 Minds tables in the same DB are
# never touched by accident.
TABLES = (
    "alembic_version",
    "attendees",
    "conversations",
    "grid_audit_runs",
    "matches",
    "messages",
    "thread_posts",
    "threads",
    "users",
)


def upgrade() -> None:
    for t in TABLES:
        op.execute(f'ALTER TABLE public."{t}" ENABLE ROW LEVEL SECURITY;')


def downgrade() -> None:
    for t in TABLES:
        op.execute(f'ALTER TABLE public."{t}" DISABLE ROW LEVEL SECURITY;')
