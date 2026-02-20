"""add_meeting_time_to_matches

Revision ID: c9a3e7f12d88
Revises: b7e2d4f09c31
Create Date: 2026-02-20 13:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c9a3e7f12d88'
down_revision: Union[str, None] = 'b7e2d4f09c31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('matches', sa.Column('meeting_time', sa.DateTime(), nullable=True))
    op.add_column('matches', sa.Column('meeting_location', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('matches', 'meeting_location')
    op.drop_column('matches', 'meeting_time')
