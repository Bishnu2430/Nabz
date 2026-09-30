"""Imaging records keep their study image and the report's title, findings and impression.

Revision ID: 9d4f1c7e2b18
Revises: 7b1e3d2a9c40
Create Date: 2026-09-30 10:01:01.671093
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '9d4f1c7e2b18'
down_revision: str | None = '7b1e3d2a9c40'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('health_record', sa.Column('image_key', sa.Text(), nullable=True))
    op.add_column('health_record', sa.Column('study', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('health_record', 'study')
    op.drop_column('health_record', 'image_key')
