"""Reminders, home readings with the person's own targets, and the emergency card's details.

Revision ID: b7d2f4a91c36
Revises: a3c5e8f10d27
Create Date: 2026-10-01 06:52:50.724047
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'b7d2f4a91c36'
down_revision: str | None = 'a3c5e8f10d27'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('home_reading',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('profile_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.Enum('bp', 'glucose', 'weight', 'pulse', 'temperature', 'spo2', name='reading_kind'), nullable=False),
    sa.Column('value', sa.Numeric(), nullable=False),
    sa.Column('value2', sa.Numeric(), nullable=True),
    sa.Column('context', sa.Text(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('taken_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['profile.id'], name=op.f('fk_home_reading_profile_id_profile'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_home_reading'))
    )
    op.create_index('ix_home_reading_profile_kind_time', 'home_reading', ['profile_id', 'kind', sa.literal_column('taken_at DESC')], unique=False)
    op.create_table('reminder',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('profile_id', sa.UUID(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('test_code', sa.Text(), nullable=True),
    sa.Column('due_on', sa.Date(), nullable=False),
    sa.Column('repeat_months', sa.SmallInteger(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('done_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['app_user.id'], name=op.f('fk_reminder_created_by_app_user'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['profile_id'], ['profile.id'], name=op.f('fk_reminder_profile_id_profile'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reminder'))
    )
    op.create_index('ix_reminder_due', 'reminder', ['due_on'], unique=False, postgresql_where=sa.text('done_at IS NULL'))
    op.create_index(op.f('ix_reminder_profile_id'), 'reminder', ['profile_id'], unique=False)
    op.add_column('profile', sa.Column('emergency', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('profile', sa.Column('reading_targets', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('profile', 'reading_targets')
    op.drop_column('profile', 'emergency')
    op.drop_index(op.f('ix_reminder_profile_id'), table_name='reminder')
    op.drop_index('ix_reminder_due', table_name='reminder', postgresql_where=sa.text('done_at IS NULL'))
    op.drop_table('reminder')
    op.drop_index('ix_home_reading_profile_kind_time', table_name='home_reading')
    op.drop_table('home_reading')
    sa.Enum(name='reading_kind').drop(op.get_bind(), checkfirst=True)
