#!/usr/bin/env python3
"""Test the new matcher with existing dataset data."""

import sys
sys.path.insert(0, '/home/ben/Documents/GitHub/data-migrator/backend')

from app.core.matcher import HeaderMatcher

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
            "State"
        ]
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
            "Proposal Status"
        ]
    }
]

print("=" * 80)
print("TESTING NEW ODOO FIELD MATCHER")
print("=" * 80)

for test in test_cases:
    sheet_name = test["sheet_name"]
    columns = test["columns"]

    print(f"\n\nSheet: {sheet_name}")
    print("-" * 60)

    # Initialize matcher (will auto-detect model)
    matcher = HeaderMatcher(target_model=None)

    print("\nMAPPINGS:")
    print("-" * 60)

    for column in columns:
        # Get mapping suggestions
        candidates = matcher.match(
            header=column,
            sheet_name=sheet_name,
            column_names=columns
        )

        # Get top candidate
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