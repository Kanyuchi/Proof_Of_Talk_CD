"""add_two_sided_status_to_matches

Revision ID: b7e2d4f09c31
Revises: a3f1c8e92b45
Create Date: 2026-02-20 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b7e2d4f09c31'
down_revision: Union[str, None] = 'a3f1c8e92b45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Per-party status columns — "pending", "accepted", "declined"
    op.add_column('matches', sa.Column(
        'status_a', sa.String(50), nullable=False, server_default='pending'
    ))
    op.add_column('matches', sa.Column(
        'status_b', sa.String(50), nullable=False, server_default='pending'
    ))
    # Back-fill: copy existing status into both sides so old accepted/declined
    # matches remain coherent after the migration.
    op.execute("""
        UPDATE matches
        SET status_a = status,
            status_b = status
        WHERE status IN ('accepted', 'declined', 'met')
    """)


def downgrade() -> None:
    op.drop_column('matches', 'status_b')
    op.drop_column('matches', 'status_a')
