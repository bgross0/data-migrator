"""add graph run context columns

Revision ID: 26ec48b04825
Revises: a1f801fbf689
Create Date: 2025-10-19 13:52:36.957932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26ec48b04825'
down_revision: Union[str, None] = 'a1f801fbf689'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("graph_runs", sa.Column("current_node", sa.String(), nullable=True))
    op.add_column("graph_runs", sa.Column("context", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("graph_runs", "context")
    op.drop_column("graph_runs", "current_node")
