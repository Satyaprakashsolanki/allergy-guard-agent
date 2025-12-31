"""Add cuisine_hint and allergens_used columns to scans table

Revision ID: 001_add_scan_context
Revises:
Create Date: 2024-12-31

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '001_add_scan_context'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cuisine_hint and allergens_used columns to scans table."""
    # Add cuisine_hint column - stores cuisine type detected or provided
    op.add_column(
        'scans',
        sa.Column('cuisine_hint', sa.String(100), nullable=True)
    )

    # Add allergens_used column - stores user's allergens at scan time
    op.add_column(
        'scans',
        sa.Column('allergens_used', JSONB, nullable=True, server_default='[]')
    )


def downgrade() -> None:
    """Remove cuisine_hint and allergens_used columns from scans table."""
    op.drop_column('scans', 'allergens_used')
    op.drop_column('scans', 'cuisine_hint')
