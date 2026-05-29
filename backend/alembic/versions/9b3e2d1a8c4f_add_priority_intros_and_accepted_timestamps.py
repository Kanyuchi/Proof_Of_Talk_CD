"""add_priority_intros_and_accepted_timestamps

Revision ID: 9b3e2d1a8c4f
Revises: 24a02695202e
Create Date: 2026-05-28 20:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9b3e2d1a8c4f"
down_revision: Union[str, None] = "24a02695202e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "requested_intros",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("requester_attendee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_attendee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_name_raw", sa.Text(), nullable=False),
        sa.Column("target_company_raw", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["requester_attendee_id"], ["attendees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_attendee_id"], ["attendees.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_requested_intros_requester",
        "requested_intros",
        ["requester_attendee_id"],
    )
    op.create_index(
        "ix_requested_intros_target",
        "requested_intros",
        ["target_attendee_id"],
    )
    op.create_unique_constraint(
        "uq_requested_intros_dedup",
        "requested_intros",
        ["requester_attendee_id", "target_name_raw", "target_company_raw"],
    )

    op.add_column("matches", sa.Column("accepted_a_at", sa.DateTime(), nullable=True))
    op.add_column("matches", sa.Column("accepted_b_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "accepted_b_at")
    op.drop_column("matches", "accepted_a_at")
    op.drop_constraint("uq_requested_intros_dedup", "requested_intros", type_="unique")
    op.drop_index("ix_requested_intros_target", table_name="requested_intros")
    op.drop_index("ix_requested_intros_requester", table_name="requested_intros")
    op.drop_table("requested_intros")
