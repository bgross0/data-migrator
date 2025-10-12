#!/usr/bin/env python3
"""
Diagnostic Script for Failing Field Matches

Analyzes the 4 remaining failing fields to understand why they're not matching correctly.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.hybrid_matcher import HybridMatcher
from ground_truth import GROUND_TRUTH
import pandas as pd


def diagnose_field(matcher: HybridMatcher, header: str, column_names: list, expected: tuple, test_name: str):
    """Diagnose why a field is not matching correctly."""
    print(f"\n{'='*80}")
    print(f"DIAGNOSING: {header}")
    print(f"{'='*80}")
    print(f"Test: {test_name}")
    print(f"Expected: {expected[0]}.{expected[1]}")

    # Get top 5 candidates
    candidates = matcher.match(
        header=header,
        sheet_name=test_name,
        column_names=column_names
    )

    if not candidates:
        print("\n❌ NO MATCHES FOUND")
        return

    print(f"\nTop Candidates:")
    for i, candidate in enumerate(candidates[:5], 1):
        model = candidate.get("model")
        field = candidate.get("field")
        confidence = candidate.get("confidence", 0)
        method = candidate.get("method", "unknown")
        rationale = candidate.get("rationale", "")

        is_expected = (model == expected[0] and field == expected[1])
        marker = "✓ EXPECTED" if is_expected else "✗"

        print(f"\n{i}. {marker} {model}.{field}")
        print(f"   Confidence: {confidence:.3f}")
        print(f"   Method: {method}")
        print(f"   Rationale: {rationale}")

    # Check if expected is in candidates
    expected_found = any(
        c.get("model") == expected[0] and c.get("field") == expected[1]
        for c in candidates
    )

    if expected_found:
        expected_rank = next(
            i+1 for i, c in enumerate(candidates)
            if c.get("model") == expected[0] and c.get("field") == expected[1]
        )
        print(f"\n✓ Expected match found at rank #{expected_rank}")
    else:
        print(f"\n❌ Expected match NOT in top candidates")

    print("\n" + "="*80)


def run_diagnostics():
    """Run diagnostics on all failing fields."""
    print("="*80)
    print("FIELD MATCHING DIAGNOSTICS")
    print("="*80)
    print("Analyzing 4 failing fields to identify root causes")

    # Initialize HybridMatcher
    dictionary_path = Path(__file__).parent.parent.parent.parent / "odoo-dictionary"
    print(f"\nInitializing HybridMatcher with dictionary: {dictionary_path}")
    matcher = HybridMatcher(dictionary_path=dictionary_path)

    # Failure 1: Tasks - "Assigned To"
    tasks_df = pd.DataFrame({
        "Task Title": ["Design Homepage", "Implement Backend"],
        "Project": ["Website Development", "Mobile App"],
        "Assigned To": ["Designer 1", "Developer 1"],
        "Due Date": ["2024-02-15", "2024-03-31"],
        "Priority": ["High", "Medium"],
        "Status": ["In Progress", "Ready"],
    })

    diagnose_field(
        matcher,
        "Assigned To",
        tasks_df.columns.tolist(),
        GROUND_TRUTH["tasks"]["Assigned To"],
        "Tasks"
    )

    # Failure 2: Tasks - "Status"
    diagnose_field(
        matcher,
        "Status",
        tasks_df.columns.tolist(),
        GROUND_TRUTH["tasks"]["Status"],
        "Tasks"
    )

    # Failure 3: Invoices - "Status"
    invoices_df = pd.DataFrame({
        "Invoice Number": ["INV-001", "INV-002"],
        "Customer": ["Acme Corp", "TechStart Inc"],
        "Invoice Date": ["2024-01-15", "2024-01-16"],
        "Due Date": ["2024-02-15", "2024-02-16"],
        "Subtotal": [1000.00, 2000.00],
        "Tax": [100.00, 200.00],
        "Total": [1100.00, 2200.00],
        "Status": ["posted", "draft"],
    })

    diagnose_field(
        matcher,
        "Status",
        invoices_df.columns.tolist(),
        GROUND_TRUTH["invoices"]["Status"],
        "Invoices"
    )

    # Failure 4: Financial Analysis - "Discount Band"
    financial_df = pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-02"],
        "Product": ["Widget A", "Gadget B"],
        "Segment": ["Enterprise", "SMB"],
        "Country": ["USA", "Canada"],
        "Units Sold": [100, 50],
        "Revenue": [2999.00, 2499.50],
        "COGS": [1500.00, 1250.00],
        "Profit": [1499.00, 1249.50],
        "Discount Band": ["None", "5%"],
    })

    diagnose_field(
        matcher,
        "Discount Band",
        financial_df.columns.tolist(),
        GROUND_TRUTH["financial_analysis"]["Discount Band"],
        "Financial Analysis"
    )

    print("\n" + "="*80)
    print("DIAGNOSTICS COMPLETE")
    print("="*80)
    print("\nNext Steps:")
    print("1. Review confidence scores - if expected match has low confidence, boost patterns")
    print("2. Check for competing fields - if wrong field is ranked #1, adjust priorities")
    print("3. Review rationale - understand why matcher is choosing wrong field")
    print("="*80)


if __name__ == "__main__":
    run_diagnostics()
