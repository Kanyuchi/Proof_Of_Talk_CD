"""add attendees.last_interest_notified_at

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attendees",
        sa.Column("last_interest_notified_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("attendees", "last_interest_notified_at")
