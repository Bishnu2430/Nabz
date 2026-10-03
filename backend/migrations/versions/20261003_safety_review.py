"""A clinical reviewer's verdicts on blocked explanations, question replies and unhelpful explanations.

Revision ID: f64d7ddc8715
Revises: 3206cbacf09c
Create Date: 2026-10-03 03:35:29.150182
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'f64d7ddc8715'
down_revision: str | None = '3206cbacf09c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('safety_review',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('subject_type', sa.Text(), nullable=False),
    sa.Column('subject_id', sa.UUID(), nullable=False),
    sa.Column('reviewer_id', sa.UUID(), nullable=True),
    sa.Column('verdict', sa.Text(), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['reviewer_id'], ['app_user.id'], name=op.f('fk_safety_review_reviewer_id_app_user'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_safety_review'))
    )
    op.create_index('ix_safety_review_subject', 'safety_review', ['subject_type', 'subject_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_safety_review_subject', table_name='safety_review')
    op.drop_table('safety_review')
