#!/usr/bin/env python3
"""
Test the simple HeaderMatcher against the validation suite.

This script tests the existing simple HeaderMatcher (from matcher.py) that uses:
- Hardcoded patterns from ODOO_FIELD_MAPPINGS
- Fuzzy string matching
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.matcher import HeaderMatcher
from ground_truth import GROUND_TRUTH
import pandas as pd


def test_simple_matcher():
    """Test simple HeaderMatcher with validation test cases."""
    print("="*80)
    print("TESTING SIMPLE HEADERMATCHER")
    print("="*80)

    print(f"\nInitializing simple HeaderMatcher")
    matcher = HeaderMatcher(target_model=None)

    # Test 1: Customers
    print("\n" + "="*80)
    print("TEST 1: CUSTOMERS")
    print("="*80)

    customer_df = pd.DataFrame({
        "Customer Name": ["Acme Corp", "TechStart Inc"],
        "Contact Email": ["sales@acme.com", "hello@techstart.com"],
        "Phone": ["+1-555-0100", "+1-555-0200"],
        "Street Address": ["123 Main St", "456 Tech Blvd"],
        "City": ["New York", "San Francisco"],
        "State": ["NY", "CA"],
        "Zip Code": ["10001", "94102"],
        "Annual Revenue": [1000000, 500000],
        "Customer ID": ["CUST001", "CUST002"],
    })

    customers_gt = GROUND_TRUTH["customers"]
    test_matcher(matcher, customer_df, customers_gt, "Customers")

    # Test 2: Products
    print("\n" + "="*80)
    print("TEST 2: PRODUCTS")
    print("="*80)

    products_df = pd.DataFrame({
        "Product Name": ["Widget A", "Gadget B"],
        "SKU": ["WID-001", "GAD-002"],
        "Sale Price": [29.99, 49.99],
        "Cost Price": [15.00, 25.00],
        "Category": ["Electronics", "Hardware"],
        "Barcode": ["1234567890123", "9876543210987"],
        "Active": [True, True],
    })

    products_gt = GROUND_TRUTH["products"]
    test_matcher(matcher, products_df, products_gt, "Products")

    # Test 3: Sales Orders
    print("\n" + "="*80)
    print("TEST 3: SALES ORDERS")
    print("="*80)

    orders_df = pd.DataFrame({
        "Order Number": ["SO-001", "SO-002"],
        "Customer": ["Acme Corp", "TechStart Inc"],
        "Order Date": ["2024-01-15", "2024-01-16"],
        "Total": [1500.00, 2500.00],
        "Status": ["confirmed", "draft"],
        "Salesperson": ["John Doe", "Jane Smith"],
    })

    orders_gt = GROUND_TRUTH["sales_orders"]
    test_matcher(matcher, orders_df, orders_gt, "Orders")


def test_matcher(matcher, df, ground_truth, test_name):
    """Test matcher against a dataframe with ground truth."""
    column_names = df.columns.tolist()

    correct = 0
    incorrect = 0
    missing = 0

    print(f"\nColumns: {len(column_names)}")
    print(f"Ground truth entries: {len(ground_truth)}")
    print("\nResults:")
    print("-" * 80)

    for column in column_names:
        expected = ground_truth.get(column)

        # Get match from simple matcher
        candidates = matcher.match(
            header=column,
            sheet_name=test_name,
            column_names=column_names
        )

        if candidates:
            predicted = (candidates[0]["model"], candidates[0]["field"])
            confidence = candidates[0]["confidence"]
            method = candidates[0].get("method", "pattern")

            if expected:
                if predicted == expected:
                    status = "✓ CORRECT"
                    correct += 1
                elif predicted[1] is None:
                    status = "✗ MISSING "
                    missing += 1
                else:
                    status = "✗ WRONG  "
                    incorrect += 1

                print(f"{status} | {column:20} → {predicted[0]:20}.{predicted[1] or 'None':20} (conf: {confidence:.2f}, method: {method})")
                if status == "✗ WRONG  ":
                    print(f"         | Expected: {expected[0]:20}.{expected[1]:20}")
            else:
                print(f"  NO GT  | {column:20} → {predicted[0]:20}.{predicted[1] or 'None':20} (conf: {confidence:.2f})")
        else:
            if expected:
                status = "✗ MISSING "
                missing += 1
                print(f"{status} | {column:20} → NO MATCH")
            else:
                print(f"  NO GT  | {column:20} → NO MATCH")

    # Calculate metrics
    total = len(ground_truth)
    accuracy = correct / total if total > 0 else 0.0

    print("\n" + "-" * 80)
    print(f"SUMMARY:")
    print(f"  Correct:   {correct}/{total} ({accuracy*100:.1f}%)")
    print(f"  Incorrect: {incorrect}/{total}")
    print(f"  Missing:   {missing}/{total}")
    print(f"  Accuracy:  {accuracy*100:.1f}%")

    return accuracy


if __name__ == "__main__":
    test_simple_matcher()
