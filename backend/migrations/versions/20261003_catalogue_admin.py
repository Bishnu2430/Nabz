"""Catalogue administration: proposed critical limits awaiting clinical sign-off, and a revision number.

Revision ID: 8cdf080aeeed
Revises: 6f017d8c1a36
Create Date: 2026-10-03 09:15:17.585828
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '8cdf080aeeed'
down_revision: str | None = '6f017d8c1a36'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('catalogue_revision',
    sa.Column('id', sa.SmallInteger(), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('changed_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_catalogue_revision'))
    )
    op.add_column('critical_limit', sa.Column('proposed_low', sa.Numeric(), nullable=True))
    op.add_column('critical_limit', sa.Column('proposed_high', sa.Numeric(), nullable=True))
    op.add_column('critical_limit', sa.Column('proposed_by', sa.Text(), nullable=True))
    op.add_column('critical_limit', sa.Column('proposed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('critical_limit', sa.Column('proposal_note', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('critical_limit', 'proposal_note')
    op.drop_column('critical_limit', 'proposed_at')
    op.drop_column('critical_limit', 'proposed_by')
    op.drop_column('critical_limit', 'proposed_high')
    op.drop_column('critical_limit', 'proposed_low')
    op.drop_table('catalogue_revision')
