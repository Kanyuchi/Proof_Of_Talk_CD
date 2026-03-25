"""add_target_companies

Revision ID: a1c9d5e72f33
Revises: f7b2a9c43e11
Create Date: 2026-03-25 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1c9d5e72f33'
down_revision: Union[str, None] = 'f7b2a9c43e11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('attendees', sa.Column('target_companies', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('attendees', 'target_companies')
