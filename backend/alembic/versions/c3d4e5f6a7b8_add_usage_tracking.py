"""add usage tracking — last_login_at, last_seen_at, usage_daily

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-24 12:00:00.000000

Adoption & Usage tracking: two nullable "most recent activity" timestamps
plus a tiny per-day snapshot table. See
docs/superpowers/specs/2026-05-24-adoption-usage-tracking-design.md.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(), nullable=True))
    op.add_column("attendees", sa.Column("last_seen_at", sa.DateTime(), nullable=True))
    op.create_table(
        "usage_daily",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("total_accounts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("real_accounts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_today", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cumulative_active", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("usage_daily")
    op.drop_column("attendees", "last_seen_at")
    op.drop_column("users", "last_login_at")
