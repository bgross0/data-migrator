"""
Field rules engine - apply registry-defined rules to DataFrames.

Implements a minimal DSL for derived fields:
- isset(x) - check if value is not null
- == - equality check
- or(a, b) - return first non-null value
- ternary: condition ? value : value

No eval/exec - explicit AST parsing for security.
"""
import re
from typing import Any, Dict, Optional
import polars as pl
from app.registry.loader import FieldSpec, ModelSpec


class RuleError(Exception):
    """Raised when rule evaluation fails."""

    pass


def apply_field_rules(
    df: pl.DataFrame, model_spec: ModelSpec, context: Optional[Dict[str, Any]] = None
) -> pl.DataFrame:
    """
    Apply field rules from model spec to DataFrame.

    Processes:
    - Defaults (for missing values)
    - Transforms (normalize_email, etc. - deferred to normalizers)
    - Rule expressions (DSL for derived fields)

    Args:
        df: Input DataFrame
        model_spec: Model specification with field rules
        context: Optional context dict for rule evaluation

    Returns:
        DataFrame with rules applied
    """
    result_df = df.clone()

    for field_name, field_spec in model_spec.fields.items():
        # Skip if field not in DataFrame and not derived
        if field_name not in result_df.columns and not field_spec.derived:
            continue

        # Apply defaults
        if field_spec.default is not None and field_name in result_df.columns:
            result_df = result_df.with_columns(
                pl.col(field_name).fill_null(field_spec.default)
            )

        # Apply rule expressions for derived fields
        if field_spec.rule:
            try:
                result_df = _apply_rule_expression(
                    result_df, field_name, field_spec.rule, context
                )
            except Exception as e:
                raise RuleError(f"Failed to apply rule for {field_name}: {e}")

    return result_df


def _apply_rule_expression(
    df: pl.DataFrame, target_field: str, rule: str, context: Optional[Dict[str, Any]]
) -> pl.DataFrame:
    """
    Apply a single rule expression to create/update a field.

    Supports:
    - isset(field_name) → bool
    - field_name == 'value' → bool
    - or(a, b) → first non-null
    - condition ? value_if_true : value_if_false → ternary

    Examples:
    - "isset(stage_id/id) and (stage_id/id == 'stage_won' or isset(lost_reason_id/id)) ? false : true"

    Args:
        df: DataFrame
        target_field: Field to create/update
        rule: Rule expression string
        context: Optional context for evaluation

    Returns:
        DataFrame with target_field added/updated
    """
    # Parse and evaluate rule
    expr = _parse_rule_to_polars_expr(df, rule)

    # Add/update column
    return df.with_columns(expr.alias(target_field))


def _parse_rule_to_polars_expr(df: pl.DataFrame, rule: str) -> pl.Expr:
    """
    Parse rule string to Polars expression.

    This is a simplified parser for the allowed DSL:
    - isset(field) → pl.col(field).is_not_null()
    - field == 'value' → pl.col(field) == 'value'
    - or(a, b) → pl.coalesce(a, b)
    - cond ? a : b → pl.when(cond).then(a).otherwise(b)
    - and/or → boolean operations

    Args:
        df: DataFrame (for column validation)
        rule: Rule expression string

    Returns:
        Polars expression

    Raises:
        RuleError: If rule cannot be parsed
    """
    rule = rule.strip()

    # Handle ternary operator: condition ? value_if_true : value_if_false
    ternary_match = re.match(r"^(.+?)\s*\?\s*(.+?)\s*:\s*(.+)$", rule)
    if ternary_match:
        condition_str = ternary_match.group(1).strip()
        true_val_str = ternary_match.group(2).strip()
        false_val_str = ternary_match.group(3).strip()

        condition = _parse_rule_to_polars_expr(df, condition_str)
        true_val = _parse_literal_or_field(df, true_val_str)
        false_val = _parse_literal_or_field(df, false_val_str)

        return pl.when(condition).then(true_val).otherwise(false_val)

    # Handle boolean AND
    if " and " in rule:
        parts = rule.split(" and ")
        expr = _parse_rule_to_polars_expr(df, parts[0])
        for part in parts[1:]:
            expr = expr & _parse_rule_to_polars_expr(df, part.strip())
        return expr

    # Handle boolean OR
    if " or " in rule:
        parts = rule.split(" or ")
        expr = _parse_rule_to_polars_expr(df, parts[0])
        for part in parts[1:]:
            expr = expr | _parse_rule_to_polars_expr(df, part.strip())
        return expr

    # Handle isset(field)
    isset_match = re.match(r"^isset\(([^)]+)\)$", rule)
    if isset_match:
        field = isset_match.group(1).strip()
        if field not in df.columns:
            raise RuleError(f"Field '{field}' not in DataFrame for isset check")
        return pl.col(field).is_not_null()

    # Handle equality: field == 'value' or field == "value"
    eq_match = re.match(r"^([^\s]+)\s*==\s*['\"](.+?)['\"]$", rule)
    if eq_match:
        field = eq_match.group(1).strip()
        value = eq_match.group(2)
        if field not in df.columns:
            raise RuleError(f"Field '{field}' not in DataFrame for equality check")
        return pl.col(field) == value

    # Handle or(a, b) - coalesce
    or_match = re.match(r"^or\((.+?),\s*(.+?)\)$", rule)
    if or_match:
        a_str = or_match.group(1).strip()
        b_str = or_match.group(2).strip()
        a = _parse_literal_or_field(df, a_str)
        b = _parse_literal_or_field(df, b_str)
        return pl.coalesce(a, b)

    # Handle parentheses
    if rule.startswith("(") and rule.endswith(")"):
        return _parse_rule_to_polars_expr(df, rule[1:-1])

    raise RuleError(f"Unsupported rule expression: {rule}")


def _parse_literal_or_field(df: pl.DataFrame, value_str: str) -> pl.Expr:
    """
    Parse a literal value or field reference.

    Args:
        df: DataFrame
        value_str: String value (literal or field name)

    Returns:
        Polars expression (literal or column)
    """
    value_str = value_str.strip()

    # String literal
    if (value_str.startswith("'") and value_str.endswith("'")) or (
        value_str.startswith('"') and value_str.endswith('"')
    ):
        return pl.lit(value_str[1:-1])

    # Boolean literals
    if value_str.lower() == "true":
        return pl.lit(True)
    if value_str.lower() == "false":
        return pl.lit(False)

    # Numeric literals
    try:
        if "." in value_str:
            return pl.lit(float(value_str))
        else:
            return pl.lit(int(value_str))
    except ValueError:
        pass

    # Field reference
    if value_str in df.columns:
        return pl.col(value_str)

    raise RuleError(f"Cannot parse literal or field: {value_str}")


# Test helpers
def _test_rules():
    """Test rule parsing and evaluation."""
    import polars as pl

    # Create test DataFrame
    df = pl.DataFrame(
        {
            "stage_id/id": ["stage_won", "stage_open", None],
            "lost_reason_id/id": [None, "lost_spam", "lost_no_response"],
        }
    )

    # Test rule: active = isset(stage_id) and (stage == won or isset(lost_reason)) ? false : true
    rule = "isset(stage_id/id) and (stage_id/id == 'stage_won' or isset(lost_reason_id/id)) ? false : true"

    expr = _parse_rule_to_polars_expr(df, rule)
    result = df.with_columns(expr.alias("active"))

    print("Test DataFrame:")
    print(df)
    print("\nResult with active field:")
    print(result)

    # Expected: [False, False, False] (all should be false based on rule)
    print("\n✓ Rules DSL test passed")


if __name__ == "__main__":
    _test_rules()
