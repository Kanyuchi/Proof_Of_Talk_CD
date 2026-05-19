"""add TEAM to tickettype enum

Revision ID: a7c4d1e8b2f5
Revises: f3a8c5d29014
Create Date: 2026-05-19 12:30:00.000000

Adds 'TEAM' to the tickettype enum for PoT + XVentures organising staff
who are neither delegates, speakers, sponsors, nor VIPs. Backfill of the
15 existing staff rows happens out-of-band via REST (see session_log).
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'a7c4d1e8b2f5'
down_revision: Union[str, None] = 'f3a8c5d29014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres requires ALTER TYPE ADD VALUE outside a transaction in older
    # versions; modern PG (10+) allows it inside, but Alembic still wraps
    # each migration in a transaction. Use op.execute with commit=True via
    # raw connection. Simpler: use op.execute — works on PG 12+.
    op.execute("ALTER TYPE tickettype ADD VALUE IF NOT EXISTS 'TEAM'")


def downgrade() -> None:
    # Postgres does not support removing enum values. Manual downgrade would
    # require recreating the type. Leave as no-op; downgrade is best-effort.
    pass
