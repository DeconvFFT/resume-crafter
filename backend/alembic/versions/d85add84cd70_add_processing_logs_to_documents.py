"""add_processing_logs_to_documents

Revision ID: d85add84cd70
Revises: 
Create Date: 2026-01-12 09:39:24.914377

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd85add84cd70'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add processing_logs column to documents table
    op.add_column(
        'documents',
        sa.Column('processing_logs', sa.dialects.postgresql.JSONB(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('documents', 'processing_logs')
