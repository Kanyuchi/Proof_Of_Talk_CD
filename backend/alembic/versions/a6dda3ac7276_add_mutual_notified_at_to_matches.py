"""add mutual_notified_at to matches

Reciprocity-loop dedup guard. NULL = not yet sent; cron sets this after
sending the 'mutual match confirmed' email to both parties. Prevents
re-sending on every run and decouples the email from the request path
(the inline send in update_match_status was removed in this same PR).

Revision ID: a6dda3ac7276
Revises: d4e5f6a7b8c9
Create Date: 2026-05-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a6dda3ac7276'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'matches',
        sa.Column('mutual_notified_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('matches', 'mutual_notified_at')
