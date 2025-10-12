"""add cleaned data tracking to dataset

Revision ID: 776044534d04
Revises: 5c236e0abf77
Create Date: 2025-10-12 13:20:46.815411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '776044534d04'
down_revision: Union[str, None] = '5c236e0abf77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add cleaned data tracking fields to datasets table
    op.add_column('datasets', sa.Column('cleaned_file_path', sa.String(), nullable=True))
    op.add_column('datasets', sa.Column('cleaning_report', sa.JSON(), nullable=True))
    op.add_column('datasets', sa.Column('profiling_status', sa.String(), nullable=False, server_default='pending'))


def downgrade() -> None:
    # Remove cleaned data tracking fields from datasets table
    op.drop_column('datasets', 'profiling_status')
    op.drop_column('datasets', 'cleaning_report')
    op.drop_column('datasets', 'cleaned_file_path')
