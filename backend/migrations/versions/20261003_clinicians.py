"""Clinicians: their council registration, reports a family shares with them, and their notes.

Revision ID: 6f017d8c1a36
Revises: 5ca7673af971
Create Date: 2026-10-03 08:52:55.552135
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '6f017d8c1a36'
down_revision: str | None = '5ca7673af971'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('clinician',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('full_name', sa.Text(), nullable=False),
    sa.Column('registration_no', sa.Text(), nullable=False),
    sa.Column('council', sa.Text(), nullable=False),
    sa.Column('specialty', sa.Text(), nullable=True),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('verified_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name=op.f('fk_clinician_user_id_app_user'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['verified_by'], ['app_user.id'], name=op.f('fk_clinician_verified_by_app_user'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_clinician'))
    )
    op.create_table('clinician_note',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('clinician_user_id', sa.UUID(), nullable=True),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['clinician_user_id'], ['app_user.id'], name=op.f('fk_clinician_note_clinician_user_id_app_user'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['report_id'], ['report.id'], name=op.f('fk_clinician_note_report_id_report'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_clinician_note'))
    )
    op.create_index(op.f('ix_clinician_note_report_id'), 'clinician_note', ['report_id'], unique=False)
    op.create_table('report_grant',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('clinician_user_id', sa.UUID(), nullable=False),
    sa.Column('granted_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['clinician_user_id'], ['app_user.id'], name=op.f('fk_report_grant_clinician_user_id_app_user'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['granted_by'], ['app_user.id'], name=op.f('fk_report_grant_granted_by_app_user'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['report_id'], ['report.id'], name=op.f('fk_report_grant_report_id_report'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_report_grant'))
    )
    op.create_index('ix_report_grant_clinician', 'report_grant', ['clinician_user_id', 'revoked_at'], unique=False)
    op.create_index(op.f('ix_report_grant_report_id'), 'report_grant', ['report_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_report_grant_report_id'), table_name='report_grant')
    op.drop_index('ix_report_grant_clinician', table_name='report_grant')
    op.drop_table('report_grant')
    op.drop_index(op.f('ix_clinician_note_report_id'), table_name='clinician_note')
    op.drop_table('clinician_note')
    op.drop_table('clinician')
