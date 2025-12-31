"""Add response_analyses table and database indexes

Revision ID: 002_response_analysis
Revises: 001_add_scan_context
Create Date: 2024-12-31

This migration:
1. Creates response_analyses table for persisting staff response analysis
2. Adds unique constraint to user_allergens (user_id, allergen_id)
3. Creates performance indexes on frequently queried columns
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '002_response_analysis'
down_revision: Union[str, None] = '001_add_scan_context'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create response_analyses table and add performance indexes.
    """
    # ========================
    # 1. Create response_analyses table
    # ========================
    op.create_table(
        'response_analyses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scan_id', UUID(as_uuid=True), sa.ForeignKey('scans.id', ondelete='SET NULL'), nullable=True),
        sa.Column('response_text', sa.Text, nullable=False),
        sa.Column('clarity', sa.String(20), nullable=False),  # clear, unclear, dangerous
        sa.Column('confidence', sa.Numeric(3, 2), nullable=False, server_default='0.5'),
        sa.Column('flags', JSONB, nullable=False, server_default='[]'),
        sa.Column('recommendation', sa.Text, nullable=True),
        sa.Column('allergens_checked', JSONB, nullable=True, server_default='[]'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Indexes for response_analyses
    op.create_index('idx_response_analyses_user_created', 'response_analyses', ['user_id', 'created_at'])
    op.create_index('idx_response_analyses_scan', 'response_analyses', ['scan_id'])
    op.create_index('idx_response_analyses_clarity', 'response_analyses', ['clarity'])

    # ========================
    # 2. Add unique constraint to user_allergens
    # ========================
    op.create_unique_constraint('uq_user_allergen', 'user_allergens', ['user_id', 'allergen_id'])

    # Indexes for user_allergens
    op.create_index('idx_user_allergens_user', 'user_allergens', ['user_id'])
    op.create_index('idx_user_allergens_allergen', 'user_allergens', ['allergen_id'])
    op.create_index('idx_user_allergens_severity', 'user_allergens', ['severity'])

    # ========================
    # 3. Add indexes to scans table
    # ========================
    op.create_index('idx_scans_user_created', 'scans', ['user_id', 'created_at'])
    op.create_index('idx_scans_cuisine', 'scans', ['cuisine_hint'])

    # ========================
    # 4. Add indexes to scan_dishes table
    # ========================
    op.create_index('idx_scan_dishes_scan', 'scan_dishes', ['scan_id'])
    op.create_index('idx_scan_dishes_risk', 'scan_dishes', ['risk_level'])


def downgrade() -> None:
    """
    Remove response_analyses table and all indexes.
    """
    # Drop scan_dishes indexes
    op.drop_index('idx_scan_dishes_risk', 'scan_dishes')
    op.drop_index('idx_scan_dishes_scan', 'scan_dishes')

    # Drop scans indexes
    op.drop_index('idx_scans_cuisine', 'scans')
    op.drop_index('idx_scans_user_created', 'scans')

    # Drop user_allergens indexes and constraint
    op.drop_index('idx_user_allergens_severity', 'user_allergens')
    op.drop_index('idx_user_allergens_allergen', 'user_allergens')
    op.drop_index('idx_user_allergens_user', 'user_allergens')
    op.drop_constraint('uq_user_allergen', 'user_allergens', type_='unique')

    # Drop response_analyses table (indexes are dropped automatically)
    op.drop_table('response_analyses')
