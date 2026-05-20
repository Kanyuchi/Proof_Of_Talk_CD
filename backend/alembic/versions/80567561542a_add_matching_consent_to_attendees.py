"""add matching_consent to attendees

Revision ID: 80567561542a
Revises: a7c4d1e8b2f5
Create Date: 2026-05-20 19:00:08.692671
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '80567561542a'
down_revision: Union[str, None] = 'a7c4d1e8b2f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attendees",
        sa.Column(
            "matching_consent",
            sa.String(length=32),
            server_default="not_required",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("attendees", "matching_consent")
