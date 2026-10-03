"""Share links: who the link is for, how often it was opened and when (FR-34).

Revision ID: a3c5e8f10d27
Revises: 9d4f1c7e2b18
Create Date: 2026-10-01 06:46:23.583018
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'a3c5e8f10d27'
down_revision: str | None = '9d4f1c7e2b18'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('share_link', sa.Column('label', sa.Text(), nullable=True))
    op.add_column('share_link', sa.Column('views', sa.Integer(), server_default='0', nullable=False))
    op.add_column('share_link', sa.Column('last_viewed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('share_link', 'last_viewed_at')
    op.drop_column('share_link', 'views')
    op.drop_column('share_link', 'label')
