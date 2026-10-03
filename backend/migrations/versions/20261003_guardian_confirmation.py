"""A person under 18 records when the account holder confirmed being their parent or guardian (FR-05).

Revision ID: 5ca7673af971
Revises: f64d7ddc8715
Create Date: 2026-10-03 08:40:14.069839
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '5ca7673af971'
down_revision: str | None = 'f64d7ddc8715'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('profile', sa.Column('guardian_confirmed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('profile', 'guardian_confirmed_at')
