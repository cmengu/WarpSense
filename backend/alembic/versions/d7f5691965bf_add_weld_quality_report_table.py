"""add_weld_quality_report_table

Revision ID: d7f5691965bf
Revises: 014_add_wqi_windowed_columns
Create Date: 2026-03-18 13:50:50.826505

Phase 7: weld_quality_reports table + sessions.quality_report_id FK only.
Other autogenerate noise (session_narratives, session_annotations, type changes) removed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd7f5691965bf'
down_revision: Union[str, Sequence[str], None] = '014_add_wqi_windowed_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Phase 7 weld_quality_reports + sessions.quality_report_id only."""
    op.create_table(
        'weld_quality_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('operator_id', sa.String(), nullable=False),
        sa.Column('report_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('quality_class', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('iso_5817_level', sa.String(), nullable=False),
        sa.Column('disposition', sa.String(), nullable=False),
        sa.Column('disposition_rationale', sa.String(), nullable=True),
        sa.Column('root_cause', sa.String(), nullable=True),
        sa.Column('corrective_actions', sa.JSON(), nullable=False),
        sa.Column('standards_references', sa.JSON(), nullable=False),
        sa.Column('retrieved_chunks_used', sa.JSON(), nullable=False),
        sa.Column('primary_defect_categories', sa.JSON(), nullable=False),
        sa.Column('threshold_violations', sa.JSON(), nullable=False),
        sa.Column('self_check_passed', sa.Boolean(), nullable=False),
        sa.Column('self_check_notes', sa.String(), nullable=True),
        sa.Column('llm_raw_response', sa.String(), nullable=True),
        sa.Column('agent_type', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.session_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_weld_quality_reports_disposition'), 'weld_quality_reports', ['disposition'], unique=False)
    op.create_index(op.f('ix_weld_quality_reports_operator_id'), 'weld_quality_reports', ['operator_id'], unique=False)
    op.create_index(op.f('ix_weld_quality_reports_session_id'), 'weld_quality_reports', ['session_id'], unique=True)

    op.add_column('sessions', sa.Column('quality_report_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_sessions_quality_report_id'), 'sessions', ['quality_report_id'], unique=False)
    op.create_foreign_key('sessions_quality_report_id_fkey', 'sessions', 'weld_quality_reports', ['quality_report_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema: drop sessions.quality_report_id then weld_quality_reports."""
    op.drop_constraint('sessions_quality_report_id_fkey', 'sessions', type_='foreignkey')
    op.drop_index(op.f('ix_sessions_quality_report_id'), table_name='sessions')
    op.drop_column('sessions', 'quality_report_id')

    op.drop_index(op.f('ix_weld_quality_reports_session_id'), table_name='weld_quality_reports')
    op.drop_index(op.f('ix_weld_quality_reports_operator_id'), table_name='weld_quality_reports')
    op.drop_index(op.f('ix_weld_quality_reports_disposition'), table_name='weld_quality_reports')
    op.drop_table('weld_quality_reports')
