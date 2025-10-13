"""Add lambda transformation fields to mappings

Revision ID: c12af2b81ceb
Revises: 776044534d04
Create Date: 2025-10-13 16:35:12.186025

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c12af2b81ceb'
down_revision: Union[str, None] = '776044534d04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add lambda transformation fields to mappings table
    op.add_column('mappings', sa.Column('mapping_type', sa.String(), nullable=False, server_default='direct'))
    op.add_column('mappings', sa.Column('lambda_function', sa.Text(), nullable=True))
    op.add_column('mappings', sa.Column('join_config', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove lambda transformation fields from mappings table
    op.drop_column('mappings', 'join_config')
    op.drop_column('mappings', 'lambda_function')
    op.drop_column('mappings', 'mapping_type')
