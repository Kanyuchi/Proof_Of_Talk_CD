"""add_crunchbase_pot_enriched_at_to_attendees

Revision ID: a3f1c8e92b45
Revises: 1d290c67d7e6
Create Date: 2026-02-18 18:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = 'a3f1c8e92b45'
down_revision: Union[str, None] = '1d290c67d7e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('attendees', sa.Column('crunchbase_data', JSONB, nullable=True, server_default='{}'))
    op.add_column('attendees', sa.Column('pot_history', JSONB, nullable=True, server_default='{}'))
    op.add_column('attendees', sa.Column('enriched_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('attendees', 'enriched_at')
    op.drop_column('attendees', 'pot_history')
    op.drop_column('attendees', 'crunchbase_data')
