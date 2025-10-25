"""
Wide-to-Long Pivot Service.

Detects and transforms wide-format one2many relationships into long format.

Example:
    Wide format:
        lead_name | activity_1_type | activity_1_date | activity_2_type | activity_2_date
        Deal A    | Call            | 2024-10-01      | Email           | 2024-10-02

    Long format:
        lead_name | activity_type | activity_date | sequence
        Deal A    | Call          | 2024-10-01    | 1
        Deal A    | Email         | 2024-10-02    | 2

Handles:
- Numbered column groups (activity_1, activity_2, ...)
- Field groups within numbered sets (activity_1_type, activity_1_date, ...)
- Sequence preservation
- NULL handling (skip empty rows)
- Inconsistency detection (mismatched counts)
"""
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import re
from collections import defaultdict
import pandas as pd


@dataclass
class PivotGroup:
    """
    Detected pivot group (numbered column set).

    Attributes:
        prefix: Column prefix (e.g., 'activity', 'note')
        indices: List of indices found (e.g., [1, 2, 3])
        field_pattern: Dict of field → column names
                       e.g., {'type': ['activity_1_type', 'activity_2_type'],
                              'date': ['activity_1_date', 'activity_2_date']}
        confidence: Detection confidence (0.0-1.0)
        target_entity: Inferred target entity (e.g., 'mail.activity')
    """
    prefix: str
    indices: List[int]
    field_pattern: Dict[str, List[str]]
    confidence: float
    target_entity: Optional[str] = None


@dataclass
class PivotTransformResult:
    """
    Result of pivot transformation.

    Attributes:
        long_format_data: List of dicts in long format
        parent_columns: Columns from parent table (non-pivoted)
        child_columns: Columns for child table (pivoted)
        sequence_column: Name of sequence column added
        rows_created: Number of child rows created
    """
    long_format_data: List[Dict[str, Any]]
    parent_columns: List[str]
    child_columns: List[str]
    sequence_column: str
    rows_created: int


class PivotDetector:
    """
    Detects wide-format one2many relationships in tabular data.
    """

    # Minimum number of numbered columns to consider as pivot candidate
    MIN_PIVOT_COLUMNS = 2

    # Maximum gap in sequence (e.g., activity_1, activity_3 without activity_2)
    MAX_SEQUENCE_GAP = 1

    def __init__(self):
        pass

    def detect_pivot_groups(self, column_names: List[str]) -> List[PivotGroup]:
        """
        Detect numbered column groups suitable for pivoting.

        Args:
            column_names: List of column names

        Returns:
            List of detected pivot groups
        """
        # Parse column names into (prefix, index, field) tuples
        parsed_columns = self._parse_numbered_columns(column_names)

        # Group by prefix
        prefix_groups = defaultdict(list)
        for prefix, index, field, original_col in parsed_columns:
            prefix_groups[prefix].append((index, field, original_col))

        # Analyze each prefix group
        pivot_groups = []
        for prefix, columns in prefix_groups.items():
            if len(columns) < self.MIN_PIVOT_COLUMNS:
                continue

            # Extract indices
            indices = sorted(set(idx for idx, _, _ in columns))

            # Check sequence consistency
            if not self._is_valid_sequence(indices):
                continue

            # Group by field
            field_pattern = defaultdict(list)
            for idx, field, col in columns:
                field_pattern[field if field else ''].append(col)

            # Calculate confidence
            confidence = self._calculate_pivot_confidence(indices, field_pattern)

            # Infer target entity
            target = self._infer_target_entity(prefix)

            pivot_group = PivotGroup(
                prefix=prefix,
                indices=indices,
                field_pattern=dict(field_pattern),
                confidence=confidence,
                target_entity=target
            )

            pivot_groups.append(pivot_group)

        return pivot_groups

    def _parse_numbered_columns(
        self,
        column_names: List[str]
    ) -> List[Tuple[str, int, Optional[str], str]]:
        """
        Parse numbered column names into components.

        Patterns supported:
        - prefix_N (e.g., 'activity_1')
        - prefix_N_field (e.g., 'activity_1_type')
        - prefix_field_N (e.g., 'note_date_1')

        Returns:
            List of (prefix, index, field, original_col) tuples
        """
        parsed = []

        # Pattern 1: prefix_N_field (most common)
        pattern1 = r'^([a-z_]+?)_(\d+)_([a-z_]+)$'

        # Pattern 2: prefix_N (no field suffix)
        pattern2 = r'^([a-z_]+?)_(\d+)$'

        # Pattern 3: prefix_field_N (field before index)
        pattern3 = r'^([a-z_]+?)_([a-z_]+)_(\d+)$'

        for col in column_names:
            normalized = col.lower().strip()

            # Try pattern 1
            match = re.match(pattern1, normalized)
            if match:
                prefix = match.group(1)
                index = int(match.group(2))
                field = match.group(3)
                parsed.append((prefix, index, field, col))
                continue

            # Try pattern 2
            match = re.match(pattern2, normalized)
            if match:
                prefix = match.group(1)
                index = int(match.group(2))
                parsed.append((prefix, index, None, col))
                continue

            # Try pattern 3
            match = re.match(pattern3, normalized)
            if match:
                prefix = match.group(1)
                field = match.group(2)
                index = int(match.group(3))
                parsed.append((prefix, index, field, col))
                continue

        return parsed

    def _is_valid_sequence(self, indices: List[int]) -> bool:
        """
        Check if index sequence is valid for pivoting.

        Valid if:
        - Starts at 1 or 0
        - No large gaps (≤ MAX_SEQUENCE_GAP)
        """
        if not indices:
            return False

        # Should start at 0 or 1
        if indices[0] not in [0, 1]:
            return False

        # Check gaps
        for i in range(len(indices) - 1):
            gap = indices[i + 1] - indices[i]
            if gap > self.MAX_SEQUENCE_GAP + 1:
                return False

        return True

    def _calculate_pivot_confidence(
        self,
        indices: List[int],
        field_pattern: Dict[str, List[str]]
    ) -> float:
        """
        Calculate confidence score for pivot group.

        Factors:
        - Sequence completeness (no gaps)
        - Consistent field structure across indices
        - Number of fields per index
        """
        score = 0.0

        # Factor 1: Sequence completeness (0-0.4)
        expected_count = indices[-1] - indices[0] + 1
        actual_count = len(indices)
        completeness = actual_count / expected_count
        score += 0.4 * completeness

        # Factor 2: Field consistency (0-0.4)
        # All indices should have same fields
        if field_pattern:
            field_counts = [len(cols) for cols in field_pattern.values()]
            if len(set(field_counts)) == 1:
                # Perfectly consistent
                score += 0.4
            else:
                # Partially consistent
                consistency = min(field_counts) / max(field_counts)
                score += 0.4 * consistency

        # Factor 3: Multiple fields per index (0-0.2)
        num_fields = len(field_pattern)
        if num_fields >= 3:
            score += 0.2
        elif num_fields == 2:
            score += 0.1

        return min(score, 1.0)

    def _infer_target_entity(self, prefix: str) -> Optional[str]:
        """Infer target entity from column prefix."""
        prefix_lower = prefix.lower()

        if 'activity' in prefix_lower or 'task' in prefix_lower:
            return 'mail.activity'
        if 'note' in prefix_lower or 'message' in prefix_lower or 'comment' in prefix_lower:
            return 'mail.message'
        if 'line' in prefix_lower or 'item' in prefix_lower:
            return 'sale.order.line'
        if 'tag' in prefix_lower:
            return 'tags'

        return None


class PivotTransformer:
    """
    Transforms wide-format data to long-format.
    """

    def __init__(self):
        pass

    def transform_to_long(
        self,
        wide_data: List[Dict[str, Any]],
        pivot_group: PivotGroup,
        parent_key_columns: List[str]
    ) -> PivotTransformResult:
        """
        Transform wide-format data to long format.

        Args:
            wide_data: Source data in wide format
            pivot_group: Detected pivot group to transform
            parent_key_columns: Columns that identify the parent record

        Returns:
            PivotTransformResult with long-format data
        """
        long_data = []

        # Identify parent columns (non-pivoted)
        all_pivot_cols = []
        for cols in pivot_group.field_pattern.values():
            all_pivot_cols.extend(cols)

        parent_columns = [col for col in wide_data[0].keys() if col not in all_pivot_cols]

        # Identify child columns (pivoted, without index)
        child_columns = list(pivot_group.field_pattern.keys())

        # Transform each row
        for row in wide_data:
            # Extract parent data
            parent_data = {col: row[col] for col in parent_columns}

            # Extract child data for each index
            for seq, index in enumerate(pivot_group.indices, start=1):
                child_row = {}

                # Copy parent data
                child_row.update(parent_data)

                # Extract child fields for this index
                has_data = False
                for field, col_list in pivot_group.field_pattern.items():
                    # Find column for this index
                    matching_col = self._find_column_for_index(col_list, index)
                    if matching_col and matching_col in row:
                        value = row[matching_col]
                        child_row[field] = value
                        if value is not None and value != '':
                            has_data = True

                # Only add row if it has non-null data
                if has_data:
                    child_row['sequence'] = seq
                    long_data.append(child_row)

        return PivotTransformResult(
            long_format_data=long_data,
            parent_columns=parent_columns,
            child_columns=child_columns + ['sequence'],
            sequence_column='sequence',
            rows_created=len(long_data)
        )

    def _find_column_for_index(self, col_list: List[str], index: int) -> Optional[str]:
        """Find column name that matches the given index."""
        index_pattern = rf'_{index}(?:_|$)'
        for col in col_list:
            if re.search(index_pattern, col):
                return col
        return None

    def preview_transformation(
        self,
        wide_data: List[Dict[str, Any]],
        pivot_group: PivotGroup,
        parent_key_columns: List[str],
        sample_rows: int = 5
    ) -> Dict[str, Any]:
        """
        Generate preview of pivot transformation for user review.

        Args:
            wide_data: Source data
            pivot_group: Pivot group to preview
            parent_key_columns: Parent key columns
            sample_rows: Number of sample rows to include

        Returns:
            Dict with preview info
        """
        result = self.transform_to_long(
            wide_data[:sample_rows],
            pivot_group,
            parent_key_columns
        )

        return {
            'pivot_group': {
                'prefix': pivot_group.prefix,
                'indices': pivot_group.indices,
                'target_entity': pivot_group.target_entity,
                'confidence': f"{pivot_group.confidence:.0%}",
            },
            'transformation': {
                'parent_columns': result.parent_columns,
                'child_columns': result.child_columns,
                'sample_wide_rows': sample_rows,
                'sample_long_rows': len(result.long_format_data),
            },
            'sample_long_data': result.long_format_data,
        }
