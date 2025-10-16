"""add graphs and graph_runs tables

Revision ID: abc123def456
Revises: c12af2b81ceb
Create Date: 2025-10-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'abc123def456'
down_revision: Union[str, None] = 'c12af2b81ceb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create graphs table
    op.create_table(
        'graphs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('spec', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_graphs_id'), 'graphs', ['id'], unique=False)

    # Create graph_runs table
    op.create_table(
        'graph_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('graph_id', sa.String(), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='queued'),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('logs', sa.JSON(), nullable=True),
        sa.Column('stats', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['graph_id'], ['graphs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='SET NULL')
    )
    op.create_index(op.f('ix_graph_runs_id'), 'graph_runs', ['id'], unique=False)
    op.create_index(op.f('ix_graph_runs_graph_id'), 'graph_runs', ['graph_id'], unique=False)


def downgrade() -> None:
    # Drop graph_runs table
    op.drop_index(op.f('ix_graph_runs_graph_id'), table_name='graph_runs')
    op.drop_index(op.f('ix_graph_runs_id'), table_name='graph_runs')
    op.drop_table('graph_runs')

    # Drop graphs table
    op.drop_index(op.f('ix_graphs_id'), table_name='graphs')
    op.drop_table('graphs')
