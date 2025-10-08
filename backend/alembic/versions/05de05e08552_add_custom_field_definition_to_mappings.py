"""add_custom_field_definition_to_mappings

Revision ID: 05de05e08552
Revises: 8204a2bbd178
Create Date: 2025-10-07 20:28:21.483617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05de05e08552'
down_revision: Union[str, None] = '8204a2bbd178'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'mappings',
        sa.Column('custom_field_definition', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('mappings', 'custom_field_definition')
