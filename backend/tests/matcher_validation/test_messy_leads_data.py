#!/usr/bin/env python3
"""
Validation Test for messy_leads_data.csv

This test validates the HybridMatcher against a CSV file with messy contact data.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.hybrid_matcher import HybridMatcher
import pandas as pd

# Ground truth for messy_leads_data.csv
# Note: Despite the filename, this is actually contact data (res.partner),
# not lead/opportunity data (crm.lead), as it lacks lead-specific fields
# like "Opportunity Title", "Expected Revenue", "Lead Status", etc.
GROUND_TRUTH = {
    "Name": ("res.partner", "name"),
    "Phone": ("res.partner", "phone"),
    "Email": ("res.partner", "email"),
}


def test_messy_leads_data():
    """Test matcher on messy_leads_data.csv"""

    print("=" * 80)
    print("MESSY LEADS DATA VALIDATION TEST")
    print("=" * 80)

    # Load file
    file_path = Path("/home/zlab/data-migrator/messy_leads_data.csv")
    df = pd.read_csv(file_path)

    print(f"\nFile: {file_path.name}")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"Column Names: {list(df.columns)}")

    # Show data quality issues
    print(f"\nData Quality Observations:")
    print(f"  - Name formats: Various (normal, UPPERCASE, Last-First, with titles)")
    print(f"  - Phone formats: Various separators (dash, dot, parentheses, none)")
    print(f"  - Email formats: Various cases (lowercase, UPPERCASE, Mixed)")
    print(f"  - Missing values: {df.isnull().sum().sum()} total")

    # Initialize matcher
    dictionary_path = Path(__file__).parent.parent.parent.parent / "odoo-dictionary"
    matcher = HybridMatcher(dictionary_path=dictionary_path)

    # Get column names
    column_names = df.columns.tolist()

    print(f"\n{'=' * 80}")
    print("MATCHING RESULTS")
    print(f"{'=' * 80}")

    results = []
    correct = 0
    total = len(GROUND_TRUTH)

    for header in column_names:
        expected_model, expected_field = GROUND_TRUTH.get(header, (None, None))

        # Get match from HybridMatcher
        candidates = matcher.match(
            header=header,
            sheet_name="messy_leads_data",
            column_names=column_names
        )

        if candidates:
            top_match = candidates[0]
            matched_model = top_match.get("model")
            matched_field = top_match.get("field")
            confidence = top_match.get("confidence", 0.0)
            method = top_match.get("method", "unknown")

            is_correct = (matched_model == expected_model and matched_field == expected_field)
            if is_correct:
                correct += 1

            status = "✓" if is_correct else "✗"

            print(f"\n{status} Header: '{header}'")
            print(f"   Expected: {expected_model}.{expected_field}")
            print(f"   Matched:  {matched_model}.{matched_field}")
            print(f"   Confidence: {confidence:.3f}")
            print(f"   Method: {method}")

            results.append({
                "header": header,
                "expected_model": expected_model,
                "expected_field": expected_field,
                "matched_model": matched_model,
                "matched_field": matched_field,
                "confidence": confidence,
                "method": method,
                "correct": is_correct,
            })
        else:
            print(f"\n✗ Header: '{header}'")
            print(f"   Expected: {expected_model}.{expected_field}")
            print(f"   Matched:  NO MATCH")

            results.append({
                "header": header,
                "expected_model": expected_model,
                "expected_field": expected_field,
                "matched_model": None,
                "matched_field": None,
                "confidence": 0.0,
                "method": "no_match",
                "correct": False,
            })

    # Summary
    accuracy = (correct / total) * 100 if total > 0 else 0

    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total Fields: {total}")
    print(f"Correct Matches: {correct}")
    print(f"Incorrect Matches: {total - correct}")
    print(f"Accuracy: {accuracy:.1f}%")

    # Show matching methods used
    methods = {}
    for r in results:
        method = r["method"]
        methods[method] = methods.get(method, 0) + 1

    print(f"\nMatching Methods Used:")
    for method, count in sorted(methods.items(), key=lambda x: -x[1]):
        print(f"  {method}: {count}")

    # Detailed breakdown if any failures
    if correct < total:
        print(f"\n{'=' * 80}")
        print("FAILED MATCHES")
        print(f"{'=' * 80}")
        for r in results:
            if not r["correct"]:
                print(f"\n✗ {r['header']}")
                print(f"   Expected: {r['expected_model']}.{r['expected_field']}")
                print(f"   Got: {r['matched_model']}.{r['matched_field']}")
                print(f"   Confidence: {r['confidence']:.3f}")
                print(f"   Method: {r['method']}")

    # Pass/Fail
    threshold = 85.0
    if accuracy >= threshold:
        print(f"\n✓✓✓ TEST PASSED (≥{threshold}%)")
    else:
        print(f"\n✗✗✗ TEST FAILED (<{threshold}%)")

    # Additional insights
    print(f"\n{'=' * 80}")
    print("INSIGHTS")
    print(f"{'=' * 80}")
    print(f"Model Detected: res.partner (Contacts/Customers)")
    print(f"Rationale: File contains basic contact info (Name, Phone, Email)")
    print(f"           without lead-specific fields (Opportunity Title, Revenue, etc.)")
    print(f"Note: Despite filename 'messy_leads_data', content is better suited for contacts")
    print(f"\n{'=' * 80}")

    return accuracy


if __name__ == "__main__":
    accuracy = test_messy_leads_data()
    sys.exit(0 if accuracy >= 85.0 else 1)
