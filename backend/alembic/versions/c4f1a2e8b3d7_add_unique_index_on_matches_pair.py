"""add_unique_index_on_matches_pair

Adds a unique expression index on (LEAST(a, b), GREATEST(a, b)) so that the
same attendee pair can never have two Match rows regardless of which side
appears as attendee_a vs attendee_b. Closes the TOCTOU race in
`_persist_ranked` + `_apply_priority_intros` that produced 39 duplicate
Match rows in prod (audited 2026-05-29) when concurrent profile saves
fired refresh_profile_matches twice in quick succession.

Run scripts/dedupe_match_pairs.py --confirm BEFORE upgrading this revision,
or the CREATE UNIQUE INDEX will fail with a duplicate-key error.

Revision ID: c4f1a2e8b3d7
Revises: 9b3e2d1a8c4f
Create Date: 2026-05-29 14:50:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c4f1a2e8b3d7"
down_revision: Union[str, None] = "9b3e2d1a8c4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX uq_matches_pair
        ON matches (
            LEAST(attendee_a_id, attendee_b_id),
            GREATEST(attendee_a_id, attendee_b_id)
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_matches_pair;")
