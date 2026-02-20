"""add_intent_constraints_and_feedback_fields

Revision ID: d4f6c7a1b2e0
Revises: c9a3e7f12d88
Create Date: 2026-02-20 20:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4f6c7a1b2e0"
down_revision: Union[str, None] = "c9a3e7f12d88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attendees",
        sa.Column(
            "seeking",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "attendees",
        sa.Column(
            "not_looking_for",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "attendees",
        sa.Column(
            "preferred_geographies",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column("attendees", sa.Column("deal_stage", sa.String(length=100), nullable=True))

    op.add_column("matches", sa.Column("met_at", sa.DateTime(), nullable=True))
    op.add_column("matches", sa.Column("meeting_outcome", sa.String(length=100), nullable=True))
    op.add_column("matches", sa.Column("satisfaction_score", sa.Float(), nullable=True))
    op.add_column("matches", sa.Column("decline_reason", sa.Text(), nullable=True))
    op.add_column(
        "matches",
        sa.Column("hidden_by_user", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("matches", sa.Column("explanation_confidence", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "explanation_confidence")
    op.drop_column("matches", "hidden_by_user")
    op.drop_column("matches", "decline_reason")
    op.drop_column("matches", "satisfaction_score")
    op.drop_column("matches", "meeting_outcome")
    op.drop_column("matches", "met_at")

    op.drop_column("attendees", "deal_stage")
    op.drop_column("attendees", "preferred_geographies")
    op.drop_column("attendees", "not_looking_for")
    op.drop_column("attendees", "seeking")
