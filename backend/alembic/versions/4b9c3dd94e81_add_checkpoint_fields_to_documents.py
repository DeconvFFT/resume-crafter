"""Add checkpoint fields to documents for resumable processing

Revision ID: 4b9c3dd94e81
Revises: 3a8c2ff83e94
Create Date: 2026-01-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4b9c3dd94e81'
down_revision: Union[str, None] = '3a8c2ff83e94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add checkpoint columns for resumable document processing."""
    # Checkpoint state - stores completed steps, cached results, etc.
    op.add_column(
        'documents',
        sa.Column('checkpoint_state', postgresql.JSONB(), nullable=True)
    )

    # Current checkpoint step name
    op.add_column(
        'documents',
        sa.Column('checkpoint_step', sa.String(50), nullable=True)
    )

    # Timestamp of last checkpoint
    op.add_column(
        'documents',
        sa.Column('checkpoint_timestamp', sa.DateTime(), nullable=True)
    )

    # Processing attempt counter
    op.add_column(
        'documents',
        sa.Column('processing_attempt', sa.Integer(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    """Remove checkpoint columns."""
    op.drop_column('documents', 'processing_attempt')
    op.drop_column('documents', 'checkpoint_timestamp')
    op.drop_column('documents', 'checkpoint_step')
    op.drop_column('documents', 'checkpoint_state')
