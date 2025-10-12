"""
Cleaning report generation and formatting.

Tracks what was cleaned and provides output in multiple formats.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any
import json
from datetime import datetime


@dataclass
class CleaningReport:
    """
    Report of cleaning operations performed.

    Tracks all changes made to the data for audit trail and transparency.
    """

    # Shape information
    original_shape: Tuple[int, int] = (0, 0)
    cleaned_shape: Tuple[int, int] = (0, 0)

    # Column mappings (original → cleaned)
    column_mappings: Dict[str, str] = field(default_factory=dict)

    # Columns dropped
    columns_dropped: List[str] = field(default_factory=list)

    # Rows dropped (e.g., metadata rows before header)
    rows_dropped: int = 0

    # Per-rule statistics
    rule_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # All changes made (detailed log)
    changes: List[Dict[str, Any]] = field(default_factory=list)

    # Warnings/issues encountered
    warnings: List[str] = field(default_factory=list)

    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    config_used: Dict[str, Any] = field(default_factory=dict)

    @property
    def rows_removed(self) -> int:
        """Number of rows removed."""
        return self.original_shape[0] - self.cleaned_shape[0] if self.original_shape[0] > 0 else 0

    @property
    def columns_removed(self) -> int:
        """Number of columns removed."""
        return len(self.columns_dropped)

    @property
    def columns_renamed(self) -> int:
        """Number of columns renamed."""
        return sum(1 for orig, clean in self.column_mappings.items() if orig != clean)

    def add_rule_stats(self, rule_name: str, stats: Dict[str, Any]):
        """Add statistics for a rule execution."""
        self.rule_stats[rule_name] = stats

    def add_change(self, change: Dict[str, Any]):
        """Add a change to the log."""
        self.changes.append(change)

    def add_warning(self, warning: str):
        """Add a warning."""
        self.warnings.append(warning)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "original_shape": {"rows": self.original_shape[0], "columns": self.original_shape[1]},
            "cleaned_shape": {"rows": self.cleaned_shape[0], "columns": self.cleaned_shape[1]},
            "summary": {
                "rows_removed": self.rows_removed,
                "columns_removed": self.columns_removed,
                "columns_renamed": self.columns_renamed,
                "warnings_count": len(self.warnings),
            },
            "column_mappings": self.column_mappings,
            "columns_dropped": self.columns_dropped,
            "rule_stats": self.rule_stats,
            "changes": self.changes,
            "warnings": self.warnings,
            "config_used": self.config_used,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_summary(self) -> str:
        """Generate a text summary of the cleaning report."""
        lines = [
            "="*80,
            "DATA CLEANING REPORT",
            "="*80,
            f"Timestamp: {self.timestamp}",
            "",
            "SHAPE CHANGES:",
            f"  Original: {self.original_shape[0]} rows × {self.original_shape[1]} columns",
            f"  Cleaned:  {self.cleaned_shape[0]} rows × {self.cleaned_shape[1]} columns",
            f"  Removed:  {self.rows_removed} rows, {self.columns_removed} columns",
            "",
        ]

        if self.column_mappings:
            renamed = [(orig, clean) for orig, clean in self.column_mappings.items() if orig != clean]
            if renamed:
                lines.extend([
                    f"COLUMN RENAMES ({len(renamed)}):",
                ])
                for orig, clean in renamed[:10]:
                    lines.append(f"  '{orig}' → '{clean}'")
                if len(renamed) > 10:
                    lines.append(f"  ... and {len(renamed)-10} more")
                lines.append("")

        if self.columns_dropped:
            lines.extend([
                f"COLUMNS DROPPED ({len(self.columns_dropped)}):",
            ])
            for col in self.columns_dropped[:10]:
                lines.append(f"  '{col}'")
            if len(self.columns_dropped) > 10:
                lines.append(f"  ... and {len(self.columns_dropped)-10} more")
            lines.append("")

        if self.rule_stats:
            lines.extend([
                "RULE STATISTICS:",
            ])
            for rule_name, stats in self.rule_stats.items():
                lines.append(f"  {rule_name}:")
                for key, value in stats.items():
                    lines.append(f"    {key}: {value}")
            lines.append("")

        if self.warnings:
            lines.extend([
                f"WARNINGS ({len(self.warnings)}):",
            ])
            for warning in self.warnings[:5]:
                lines.append(f"  ⚠ {warning}")
            if len(self.warnings) > 5:
                lines.append(f"  ... and {len(self.warnings)-5} more")
            lines.append("")

        lines.append("="*80)

        return "\n".join(lines)

    def to_html(self) -> str:
        """Generate HTML report (for frontend display)."""
        # Simplified HTML for now
        html = [
            "<div class='cleaning-report'>",
            f"<h2>Data Cleaning Report</h2>",
            f"<p><strong>Timestamp:</strong> {self.timestamp}</p>",
            "",
            "<h3>Summary</h3>",
            "<ul>",
            f"<li><strong>Original:</strong> {self.original_shape[0]} rows × {self.original_shape[1]} columns</li>",
            f"<li><strong>Cleaned:</strong> {self.cleaned_shape[0]} rows × {self.cleaned_shape[1]} columns</li>",
            f"<li><strong>Rows removed:</strong> {self.rows_removed}</li>",
            f"<li><strong>Columns removed:</strong> {self.columns_removed}</li>",
            f"<li><strong>Columns renamed:</strong> {self.columns_renamed}</li>",
            "</ul>",
        ]

        renamed = [(orig, clean) for orig, clean in self.column_mappings.items() if orig != clean]
        if renamed:
            html.extend([
                "<h3>Column Renames</h3>",
                "<table>",
                "<tr><th>Original</th><th>Cleaned</th></tr>",
            ])
            for orig, clean in renamed[:20]:
                html.append(f"<tr><td>{orig}</td><td>{clean}</td></tr>")
            if len(renamed) > 20:
                html.append(f"<tr><td colspan='2'><em>... and {len(renamed)-20} more</em></td></tr>")
            html.append("</table>")

        if self.warnings:
            html.extend([
                "<h3>Warnings</h3>",
                "<ul>",
            ])
            for warning in self.warnings[:10]:
                html.append(f"<li>{warning}</li>")
            if len(self.warnings) > 10:
                html.append(f"<li><em>... and {len(self.warnings)-10} more</em></li>")
            html.append("</ul>")

        html.append("</div>")

        return "\n".join(html)

    def __str__(self) -> str:
        """String representation (summary)."""
        return self.to_summary()
