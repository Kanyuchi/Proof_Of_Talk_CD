"""add_magic_access_token_to_attendees

Revision ID: e5a8f3c21d99
Revises: 4f68cbefaf01
Create Date: 2026-03-23 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e5a8f3c21d99'
down_revision: Union[str, None] = '4f68cbefaf01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('attendees', sa.Column('magic_access_token', sa.String(length=64), nullable=True))
    op.create_index('ix_attendees_magic_access_token', 'attendees', ['magic_access_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_attendees_magic_access_token', table_name='attendees')
    op.drop_column('attendees', 'magic_access_token')
