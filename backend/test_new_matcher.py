#!/usr/bin/env python3
"""Smoke-test the HybridMatcher with existing dataset data."""

from pathlib import Path
import sys

# Ensure backend package is on the import path
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.hybrid_matcher import HybridMatcher  # noqa: E402

DICTIONARY_PATH = BACKEND_DIR.parent / "odoo-dictionary"

# Test data from the existing datasets
test_cases = [
    # From test_customers.csv
    {
        "sheet_name": "Sheet1",
        "columns": [
            "Active",
            "Annual Revenue",
            "City",
            "Company Name",
            "Contact Email",
            "Customer ID",
            "Phone",
            "State",
        ],
    },
    # From Leads.xlsx
    {
        "sheet_name": "Leads",
        "columns": [
            "Email",
            "Opportunity Title",
            "Street Address (Contact)",
            "City (Contact)",
            "Zip (Contact)",
            "Phone",
            "Source",
            "Project Type",
            "Salesperson",
            "Lead Status",
            "Tags",
            "Age",
            "Proposal Status",
        ],
    },
]

print("=" * 80)
print("TESTING HYBRID ODOO FIELD MATCHER")
print("=" * 80)

# Initialize matcher once (auto-detects model and uses knowledge base)
matcher = HybridMatcher(dictionary_path=DICTIONARY_PATH)

for test in test_cases:
    sheet_name = test["sheet_name"]
    columns = test["columns"]

    print(f"\n\nSheet: {sheet_name}")
    print("-" * 60)

    print("\nMAPPINGS:")
    print("-" * 60)

    for column in columns:
        candidates = matcher.match(
            header=column,
            sheet_name=sheet_name,
            column_names=columns,
        )

        if candidates:
            top = candidates[0]
            if top["field"]:
                print(f"{column:30} → {top['model']:20}.{top['field']:20} ({top['confidence']*100:.0f}%)")
                print(f"{'':30}   Rationale: {top['rationale']}")
            else:
                print(f"{column:30} → No suitable field found")
        else:
            print(f"{column:30} → No mapping found")

        print()

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
