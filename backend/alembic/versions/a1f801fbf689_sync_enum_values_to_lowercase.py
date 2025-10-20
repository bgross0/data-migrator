"""sync enum values to lowercase

Revision ID: a1f801fbf689
Revises: 1760583762
Create Date: 2025-10-19 12:50:02.345272

"""
from __future__ import annotations

from typing import Iterable, Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1f801fbf689"
down_revision: Union[str, None] = "1760583762"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MAPPING_STATUS_OLD = ("PENDING", "CONFIRMED", "IGNORED", "CREATE_FIELD")
MAPPING_STATUS_NEW = ("pending", "confirmed", "ignored", "create_field")

MATCH_STRATEGY_OLD = ("EMAIL", "XML_ID", "EXTERNAL_CODE", "NAME", "NAME_FUZZY", "PHONE")
MATCH_STRATEGY_NEW = ("email", "xml_id", "external_code", "name", "name_fuzzy", "phone")

RUN_STATUS_OLD = (
    "PENDING",
    "PROFILING",
    "MAPPING",
    "VALIDATING",
    "IMPORTING",
    "COMPLETED",
    "FAILED",
    "ROLLED_BACK",
)
RUN_STATUS_NEW = (
    "pending",
    "profiling",
    "mapping",
    "validating",
    "importing",
    "completed",
    "failed",
    "rolled_back",
)

LOG_LEVEL_OLD = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
LOG_LEVEL_NEW = ("debug", "info", "warning", "error", "critical")


def _convert_enum_to_lowercase_sqlite(
    table: str,
    column: str,
    enum_name: str,
    old_values: Iterable[str],
    new_values: Iterable[str],
    nullable: bool,
) -> None:
    """Rebuild column constraint for SQLite by hopping through plain String."""
    with op.batch_alter_table(table) as batch_op:
        batch_op.alter_column(
            column,
            existing_type=sa.Enum(*old_values, name=enum_name),
            type_=sa.String(),
            existing_nullable=nullable,
            nullable=nullable,
        )

    op.execute(sa.text(f"UPDATE {table} SET {column} = LOWER({column}) WHERE {column} IS NOT NULL"))

    new_enum = sa.Enum(*new_values, name=enum_name)
    with op.batch_alter_table(table) as batch_op:
        batch_op.alter_column(
            column,
            existing_type=sa.String(),
            type_=new_enum,
            existing_nullable=nullable,
            nullable=nullable,
        )


def _convert_enum_to_lowercase_postgres(
    table: str,
    column: str,
    enum_name: str,
    old_values: Iterable[str],
    new_values: Iterable[str],
    nullable: bool,
) -> None:
    """Use a temporary enum type to migrate values on PostgreSQL."""
    bind = op.get_bind()
    temp_enum_name = f"{enum_name}_tmp_lower"
    temp_enum = sa.Enum(*new_values, name=temp_enum_name)
    temp_enum.create(bind, checkfirst=True)

    # Cast existing values to text, normalise casing, then to the temp enum.
    op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE TEXT")
    op.execute(f"UPDATE {table} SET {column} = LOWER({column}) WHERE {column} IS NOT NULL")
    op.execute(
        f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {temp_enum_name} USING {column}::{temp_enum_name}"
    )

    # Drop the old enum and rename the temp one so the column keeps the original type name.
    old_enum = sa.Enum(name=enum_name)
    old_enum.drop(bind, checkfirst=True)
    op.execute(f"ALTER TYPE {temp_enum_name} RENAME TO {enum_name}")

    if not nullable:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET NOT NULL")
    else:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL")


def _convert_enum_to_lowercase(
    table: str,
    column: str,
    enum_name: str,
    old_values: Iterable[str],
    new_values: Iterable[str],
    nullable: bool = False,
) -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        _convert_enum_to_lowercase_postgres(table, column, enum_name, old_values, new_values, nullable)
    else:
        # SQLite (and others using CHECK constraints) can use the batch helper.
        _convert_enum_to_lowercase_sqlite(table, column, enum_name, old_values, new_values, nullable)


def upgrade() -> None:
    _convert_enum_to_lowercase(
        table="mappings",
        column="status",
        enum_name="mappingstatus",
        old_values=MAPPING_STATUS_OLD,
        new_values=MAPPING_STATUS_NEW,
        nullable=False,
    )

    _convert_enum_to_lowercase(
        table="relationships",
        column="match_on",
        enum_name="matchstrategy",
        old_values=MATCH_STRATEGY_OLD,
        new_values=MATCH_STRATEGY_NEW,
        nullable=False,
    )

    _convert_enum_to_lowercase(
        table="runs",
        column="status",
        enum_name="runstatus",
        old_values=RUN_STATUS_OLD,
        new_values=RUN_STATUS_NEW,
        nullable=False,
    )

    _convert_enum_to_lowercase(
        table="run_logs",
        column="level",
        enum_name="loglevel",
        old_values=LOG_LEVEL_OLD,
        new_values=LOG_LEVEL_NEW,
        nullable=False,
    )


def downgrade() -> None:
    _convert_enum_to_lowercase(
        table="run_logs",
        column="level",
        enum_name="loglevel",
        old_values=LOG_LEVEL_NEW,
        new_values=LOG_LEVEL_OLD,
        nullable=False,
    )

    _convert_enum_to_lowercase(
        table="runs",
        column="status",
        enum_name="runstatus",
        old_values=RUN_STATUS_NEW,
        new_values=RUN_STATUS_OLD,
        nullable=False,
    )

    _convert_enum_to_lowercase(
        table="relationships",
        column="match_on",
        enum_name="matchstrategy",
        old_values=MATCH_STRATEGY_NEW,
        new_values=MATCH_STRATEGY_OLD,
        nullable=False,
    )

    _convert_enum_to_lowercase(
        table="mappings",
        column="status",
        enum_name="mappingstatus",
        old_values=MAPPING_STATUS_NEW,
        new_values=MAPPING_STATUS_OLD,
        nullable=False,
    )
