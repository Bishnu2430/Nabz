"""Other health records (imaging, prescriptions, …) and a personal note on each report.

Revision ID: 7b1e3d2a9c40
Revises: cac5f9c0909e
Create Date: 2026-09-30 09:25:01.729804
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '7b1e3d2a9c40'
down_revision: str | None = 'cac5f9c0909e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('health_record',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('profile_id', sa.UUID(), nullable=False),
    sa.Column('uploaded_by', sa.UUID(), nullable=True),
    sa.Column('kind', sa.Enum('imaging', 'prescription', 'discharge', 'vaccination', 'other', name='record_kind'), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('record_date', sa.Date(), nullable=True),
    sa.Column('facility', sa.Text(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('storage_key', sa.Text(), nullable=False),
    sa.Column('mime_type', sa.Text(), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('sha256', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['profile.id'], name=op.f('fk_health_record_profile_id_profile'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['uploaded_by'], ['app_user.id'], name=op.f('fk_health_record_uploaded_by_app_user'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_health_record'))
    )
    op.create_index('ix_health_record_profile_date', 'health_record', ['profile_id', sa.literal_column('record_date DESC')], unique=False)
    op.add_column('report', sa.Column('note', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('report', 'note')
    op.drop_index('ix_health_record_profile_date', table_name='health_record')
    op.drop_table('health_record')
    sa.Enum(name='record_kind').drop(op.get_bind(), checkfirst=True)
