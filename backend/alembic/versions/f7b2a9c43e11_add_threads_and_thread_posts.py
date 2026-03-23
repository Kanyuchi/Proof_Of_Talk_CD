"""add_threads_and_thread_posts

Revision ID: f7b2a9c43e11
Revises: e5a8f3c21d99
Create Date: 2026-03-23 15:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f7b2a9c43e11'
down_revision: Union[str, None] = 'e5a8f3c21d99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'threads',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('slug', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_threads_slug', 'threads', ['slug'], unique=True)

    op.create_table(
        'thread_posts',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('thread_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_attendee_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_thread_posts_thread_id', 'thread_posts', ['thread_id'])


def downgrade() -> None:
    op.drop_index('ix_thread_posts_thread_id', table_name='thread_posts')
    op.drop_table('thread_posts')
    op.drop_index('ix_threads_slug', table_name='threads')
    op.drop_table('threads')
