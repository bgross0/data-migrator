"""
Remap Rule Engine.

Handles field value remapping based on rules defined by user or system.

Use Cases:
- Value normalization (e.g., "Yes" → True, "No" → False)
- Enum mapping (e.g., "Lead" → "New", "Opportunity" → "Qualified")
- Category remapping (e.g., "Enterprise" → "Large", "SMB" → "Small")
- Code standardization (e.g., "US" → "United States", "UK" → "United Kingdom")

Rule Types:
1. Exact match: value == "foo" → "bar"
2. Pattern match: value matches regex → replacement
3. Function: value → function(value)
4. Lookup table: value in {map} → map[value]
"""
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import re


class RuleType(str, Enum):
    EXACT = "exact"
    PATTERN = "pattern"
    FUNCTION = "function"
    LOOKUP = "lookup"


@dataclass
class RemapRule:
    """
    Value remapping rule.

    Attributes:
        rule_type: Type of rule
        source_field: Field to apply rule to
        pattern: Pattern/value to match (for exact/pattern rules)
        replacement: Replacement value/pattern
        lookup_table: Lookup dict (for lookup rules)
        function: Callable function (for function rules)
        priority: Rule priority (higher = applied first)
    """
    rule_type: RuleType
    source_field: str
    pattern: Optional[str] = None
    replacement: Optional[str] = None
    lookup_table: Optional[Dict[str, Any]] = None
    function: Optional[Callable] = None
    priority: int = 0


class RemapEngine:
    """
    Engine for applying value remapping rules to records.
    """

    def __init__(self):
        self.rules: Dict[str, List[RemapRule]] = {}  # field → list of rules

    def add_rule(self, rule: RemapRule):
        """
        Add remapping rule.

        Args:
            rule: RemapRule to add
        """
        field = rule.source_field
        if field not in self.rules:
            self.rules[field] = []
        self.rules[field].append(rule)

        # Sort by priority (descending)
        self.rules[field].sort(key=lambda r: r.priority, reverse=True)

    def add_exact_rule(
        self,
        field: str,
        match_value: str,
        replacement: str,
        priority: int = 0
    ):
        """
        Add exact match rule.

        Args:
            field: Field name
            match_value: Value to match exactly
            replacement: Replacement value
            priority: Rule priority
        """
        rule = RemapRule(
            rule_type=RuleType.EXACT,
            source_field=field,
            pattern=match_value,
            replacement=replacement,
            priority=priority
        )
        self.add_rule(rule)

    def add_pattern_rule(
        self,
        field: str,
        regex_pattern: str,
        replacement: str,
        priority: int = 0
    ):
        """
        Add regex pattern rule.

        Args:
            field: Field name
            regex_pattern: Regex to match
            replacement: Replacement (can use \\1, \\2 for groups)
            priority: Rule priority
        """
        rule = RemapRule(
            rule_type=RuleType.PATTERN,
            source_field=field,
            pattern=regex_pattern,
            replacement=replacement,
            priority=priority
        )
        self.add_rule(rule)

    def add_lookup_rule(
        self,
        field: str,
        lookup_table: Dict[str, Any],
        priority: int = 0
    ):
        """
        Add lookup table rule.

        Args:
            field: Field name
            lookup_table: Dict mapping source → target values
            priority: Rule priority
        """
        rule = RemapRule(
            rule_type=RuleType.LOOKUP,
            source_field=field,
            lookup_table=lookup_table,
            priority=priority
        )
        self.add_rule(rule)

    def add_function_rule(
        self,
        field: str,
        function: Callable[[Any], Any],
        priority: int = 0
    ):
        """
        Add function-based rule.

        Args:
            field: Field name
            function: Function to apply to value
            priority: Rule priority
        """
        rule = RemapRule(
            rule_type=RuleType.FUNCTION,
            source_field=field,
            function=function,
            priority=priority
        )
        self.add_rule(rule)

    def apply_rules(
        self,
        record: Dict[str, Any],
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Apply all rules to a record.

        Args:
            record: Source record
            fields: Fields to apply rules to (None = all fields with rules)

        Returns:
            Remapped record
        """
        remapped = record.copy()

        fields_to_process = fields if fields else self.rules.keys()

        for field in fields_to_process:
            if field not in self.rules or field not in remapped:
                continue

            value = remapped[field]

            # Apply each rule in priority order
            for rule in self.rules[field]:
                new_value = self._apply_rule(value, rule)
                if new_value is not None:
                    value = new_value
                    # Break after first match (unless rule specifies continue)

            remapped[field] = value

        return remapped

    def _apply_rule(self, value: Any, rule: RemapRule) -> Optional[Any]:
        """
        Apply single rule to value.

        Returns:
            Remapped value, or None if rule doesn't match
        """
        if value is None:
            return None

        if rule.rule_type == RuleType.EXACT:
            if str(value) == rule.pattern:
                return rule.replacement
            return None

        elif rule.rule_type == RuleType.PATTERN:
            if isinstance(value, str):
                match = re.search(rule.pattern, value)
                if match:
                    return re.sub(rule.pattern, rule.replacement, value)
            return None

        elif rule.rule_type == RuleType.LOOKUP:
            if rule.lookup_table:
                return rule.lookup_table.get(str(value))
            return None

        elif rule.rule_type == RuleType.FUNCTION:
            if rule.function:
                try:
                    return rule.function(value)
                except Exception:
                    return None
            return None

        return None

    def get_rules_for_field(self, field: str) -> List[RemapRule]:
        """Get all rules for a specific field."""
        return self.rules.get(field, [])

    def clear_rules(self, field: Optional[str] = None):
        """
        Clear rules.

        Args:
            field: Field to clear rules for (None = clear all)
        """
        if field:
            if field in self.rules:
                del self.rules[field]
        else:
            self.rules.clear()


# ==========================================================================
# COMMON REMAP FUNCTIONS
# ==========================================================================

def boolean_from_string(value: Any) -> Optional[bool]:
    """Convert string to boolean."""
    if isinstance(value, bool):
        return value

    str_val = str(value).lower().strip()
    if str_val in ['true', 'yes', '1', 'y', 't']:
        return True
    if str_val in ['false', 'no', '0', 'n', 'f']:
        return False
    return None


def normalize_country(value: str) -> str:
    """Normalize country name."""
    country_map = {
        'US': 'United States',
        'USA': 'United States',
        'UK': 'United Kingdom',
        'GB': 'United Kingdom',
    }
    return country_map.get(value.upper().strip(), value)


def normalize_stage(value: str) -> str:
    """Normalize CRM stage names."""
    stage_map = {
        'Lead': 'New',
        'Opportunity': 'Qualified',
        'Won': 'Closed Won',
        'Lost': 'Closed Lost',
    }
    return stage_map.get(value.strip(), value)


def extract_numeric(value: str) -> Optional[float]:
    """Extract numeric value from string (e.g., '$1,234.56' → 1234.56)."""
    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        # Remove currency symbols, commas
        cleaned = re.sub(r'[^\d.-]', '', value)
        try:
            return float(cleaned)
        except ValueError:
            return None

    return None
