"""Questions asked about a report and the answers given, kept for the person and the reviewer (FR-27).

Revision ID: 3206cbacf09c
Revises: b7d2f4a91c36
Create Date: 2026-10-01 07:31:37.325156
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '3206cbacf09c'
down_revision: str | None = 'b7d2f4a91c36'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('report_question',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('language', postgresql.ENUM('en', 'hi', 'or', name='lang', create_type=False), nullable=False),
    sa.Column('question', sa.Text(), nullable=False),
    sa.Column('answer', sa.Text(), nullable=False),
    sa.Column('mode', sa.Text(), nullable=False),
    sa.Column('refusal', sa.Text(), nullable=True),
    sa.Column('test_codes', postgresql.ARRAY(sa.Text()), nullable=False),
    sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('model_id', sa.Text(), nullable=True),
    sa.Column('prompt_version', sa.Text(), nullable=True),
    sa.Column('input_tokens', sa.Integer(), nullable=True),
    sa.Column('output_tokens', sa.Integer(), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['report_id'], ['report.id'], name=op.f('fk_report_question_report_id_report'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name=op.f('fk_report_question_user_id_app_user'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_report_question'))
    )
    op.create_index(op.f('ix_report_question_report_id'), 'report_question', ['report_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_report_question_report_id'), table_name='report_question')
    op.drop_table('report_question')
