"""add attendees.last_match_digest_at

Revision ID: a7b8c9d0e1f2
Revises: c4f1a2e8b3d7
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "c4f1a2e8b3d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attendees",
        sa.Column("last_match_digest_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("attendees", "last_match_digest_at")
