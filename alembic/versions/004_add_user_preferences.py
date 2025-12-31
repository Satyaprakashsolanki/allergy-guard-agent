"""Add user preferences table for context-aware AI analysis

Revision ID: 004_user_preferences
Revises: 003_oauth_support
Create Date: 2024-12-31

This migration:
1. Creates user_preferences table for storing context preferences
2. Includes favorite cuisines (JSON), risk tolerance, and dining context
3. Links to users table with cascade delete
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision: str = '004_user_preferences'
down_revision: Union[str, None] = '003_oauth_support'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create user_preferences table.
    """
    op.create_table(
        'user_preferences',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('favorite_cuisines', JSON, nullable=False, server_default='[]'),
        sa.Column('risk_tolerance', sa.String(20), nullable=False, server_default='standard'),
        sa.Column('default_dining_context', sa.String(20), nullable=False, server_default='restaurant'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Create index on user_id for faster lookups
    op.create_index('idx_user_preferences_user_id', 'user_preferences', ['user_id'])


def downgrade() -> None:
    """
    Drop user_preferences table.
    """
    op.drop_index('idx_user_preferences_user_id', 'user_preferences')
    op.drop_table('user_preferences')
