"""add ai_summary pin

Revision ID: 24a02695202e
Revises: a6dda3ac7276
Create Date: 2026-05-25 12:58:13.170912
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '24a02695202e'
down_revision: Union[str, None] = 'a6dda3ac7276'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("attendees", sa.Column("ai_summary_pinned", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("attendees", sa.Column("ai_summary_edited_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("attendees", "ai_summary_edited_at")
    op.drop_column("attendees", "ai_summary_pinned")
