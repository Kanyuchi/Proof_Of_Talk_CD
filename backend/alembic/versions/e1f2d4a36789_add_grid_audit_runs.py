"""add_grid_audit_runs

Revision ID: e1f2d4a36789
Revises: c8d4e9a17f22
Create Date: 2026-04-29 18:45:00.000000

History table for daily Grid coverage audits — one row per scheduled run.
Lets us trend coverage over time and surface newly-discovered Grid profiles
that the original name-based enrichment missed.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e1f2d4a36789'
down_revision: Union[str, None] = 'c8d4e9a17f22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'grid_audit_runs',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('total_domains', sa.Integer(), nullable=False),
        sa.Column('total_attendees', sa.Integer(), nullable=False),
        sa.Column('matched_domains', sa.Integer(), nullable=False),
        sa.Column('matched_attendees', sa.Integer(), nullable=False),
        sa.Column('had_grid_before_count', sa.Integer(), nullable=False, server_default='0'),
        # Newly-discovered profiles since the previous run — list of
        # {domain, grid_slug, grid_name} dicts. Drives the "backfill these"
        # surface on the admin dashboard.
        sa.Column('new_matches', sa.dialects.postgresql.JSONB(), nullable=False, server_default='[]'),
        # Domains that didn't resolve to a Grid profile. Useful for the
        # "should exist on Grid but doesn't" review surface.
        sa.Column('unmatched_domains', sa.dialects.postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
    )
    op.create_index('ix_grid_audit_runs_run_at', 'grid_audit_runs', ['run_at'])


def downgrade() -> None:
    op.drop_index('ix_grid_audit_runs_run_at', table_name='grid_audit_runs')
    op.drop_table('grid_audit_runs')
