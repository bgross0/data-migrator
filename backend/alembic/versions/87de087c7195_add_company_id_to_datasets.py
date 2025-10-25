"""add_company_id_to_datasets

Revision ID: 87de087c7195
Revises: 26ec48b04825
Create Date: 2025-10-24 14:45:28.416948

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '87de087c7195'
down_revision: Union[str, None] = '26ec48b04825'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add company_id column to datasets table
    op.add_column('datasets', sa.Column('company_id', sa.Integer(), nullable=True))

    # Create index on company_id for efficient queries
    op.create_index(op.f('ix_datasets_company_id'), 'datasets', ['company_id'], unique=False)


def downgrade() -> None:
    # Drop index first
    op.drop_index(op.f('ix_datasets_company_id'), table_name='datasets')

    # Drop company_id column
    op.drop_column('datasets', 'company_id')
