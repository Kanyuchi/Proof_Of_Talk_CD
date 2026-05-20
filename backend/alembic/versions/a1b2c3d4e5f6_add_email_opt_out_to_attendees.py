"""add email_opt_out to attendees

Revision ID: a1b2c3d4e5f6
Revises: 80567561542a
Create Date: 2026-05-20 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '80567561542a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'attendees',
        sa.Column(
            'email_opt_out',
            sa.Boolean(),
            server_default='false',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('attendees', 'email_opt_out')
