"""add_inferred_customer_profile

Revision ID: c8d4e9a17f22
Revises: 6a28b2ff60c9
Create Date: 2026-04-14 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = 'c8d4e9a17f22'
down_revision: Union[str, None] = '6a28b2ff60c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'attendees',
        sa.Column('inferred_customer_profile', JSONB(), nullable=False, server_default='{}'),
    )


def downgrade() -> None:
    op.drop_column('attendees', 'inferred_customer_profile')
