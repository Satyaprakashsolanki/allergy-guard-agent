"""Add OAuth support for Google Sign-In

Revision ID: 003_oauth_support
Revises: 002_response_analysis
Create Date: 2024-12-31

This migration:
1. Makes password_hash nullable (for OAuth users who don't have passwords)
2. Adds auth_provider column to track authentication method
3. Adds google_id column for Google OAuth users
4. Adds profile_picture_url for OAuth profile pictures
5. Sets existing users to auth_provider='email'
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_oauth_support'
down_revision: Union[str, None] = '002_response_analysis'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add OAuth columns to users table.
    """
    # 1. Add auth_provider column with default 'email' for existing users
    op.add_column(
        'users',
        sa.Column('auth_provider', sa.String(20), nullable=False, server_default='email')
    )

    # 2. Add google_id column (unique, nullable, indexed)
    op.add_column(
        'users',
        sa.Column('google_id', sa.String(255), nullable=True)
    )
    op.create_index('idx_users_google_id', 'users', ['google_id'], unique=True)

    # 3. Add profile_picture_url column
    op.add_column(
        'users',
        sa.Column('profile_picture_url', sa.String(500), nullable=True)
    )

    # 4. Make password_hash nullable for OAuth users
    # Note: Existing users already have password_hash, so this is safe
    op.alter_column(
        'users',
        'password_hash',
        existing_type=sa.String(255),
        nullable=True
    )

    # 5. Add index on auth_provider for filtering
    op.create_index('idx_users_auth_provider', 'users', ['auth_provider'])


def downgrade() -> None:
    """
    Remove OAuth columns from users table.

    WARNING: This will fail if any users have NULL password_hash (OAuth users).
    You must either:
    1. Delete OAuth-only users first, OR
    2. Set a placeholder password_hash for them
    """
    # Drop indexes
    op.drop_index('idx_users_auth_provider', 'users')
    op.drop_index('idx_users_google_id', 'users')

    # Drop columns
    op.drop_column('users', 'profile_picture_url')
    op.drop_column('users', 'google_id')
    op.drop_column('users', 'auth_provider')

    # Make password_hash non-nullable again
    # WARNING: Will fail if any NULL values exist
    op.alter_column(
        'users',
        'password_hash',
        existing_type=sa.String(255),
        nullable=False
    )
