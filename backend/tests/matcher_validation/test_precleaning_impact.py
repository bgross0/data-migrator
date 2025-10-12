#!/usr/bin/env python3
"""
Test Pre-Cleaning Impact on Matching Accuracy

Compares HybridMatcher accuracy with and without pre-cleaning of column names.

This test validates that the pre-cleaning module improves matching accuracy by
removing common real-world data quality issues like parenthetical suffixes,
special characters, and extra whitespace.
"""
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, List

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.hybrid_matcher import HybridMatcher
from app.cleaners.config import CleaningConfig
from app.cleaners.rules.column_name import ColumnNameCleaningRule
from ground_truth import GROUND_TRUTH, get_threshold


class PreCleaningTestResults:
    """Stores comparison results between raw and cleaned matching."""

    def __init__(self):
        self.test_cases = []
        self.start_time = datetime.now()
        self.end_time = None

    def add_test_case(self, raw_result: Dict, cleaned_result: Dict, test_name: str):
        """Add a comparison result."""
        self.test_cases.append({
            "test_name": test_name,
            "raw": raw_result,
            "cleaned": cleaned_result,
            "improvement": cleaned_result["accuracy"] - raw_result["accuracy"],
        })

    def finalize(self):
        """Finalize results."""
        self.end_time = datetime.now()

    def get_summary(self) -> Dict:
        """Get overall summary."""
        total_raw_correct = sum(r["raw"]["correct"] for r in self.test_cases)
        total_cleaned_correct = sum(r["cleaned"]["correct"] for r in self.test_cases)
        total_fields = sum(r["raw"]["total_fields"] for r in self.test_cases)

        raw_accuracy = total_raw_correct / total_fields if total_fields > 0 else 0.0
        cleaned_accuracy = total_cleaned_correct / total_fields if total_fields > 0 else 0.0
        improvement = cleaned_accuracy - raw_accuracy

        return {
            "total_test_cases": len(self.test_cases),
            "total_fields": total_fields,
            "raw_correct": total_raw_correct,
            "cleaned_correct": total_cleaned_correct,
            "raw_accuracy": raw_accuracy,
            "cleaned_accuracy": cleaned_accuracy,
            "improvement": improvement,
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else 0,
        }


def clean_column_names(column_names: List[str]) -> Tuple[List[str], Dict[str, str]]:
    """
    Clean column names using the pre-cleaning rules.

    Args:
        column_names: Original column names

    Returns:
        Tuple of (cleaned_names, mappings)
    """
    config = CleaningConfig.default()
    rule = ColumnNameCleaningRule(config)

    # Create a dummy DataFrame with the columns
    dummy_df = pd.DataFrame(columns=column_names)

    # Apply cleaning
    result = rule.clean(dummy_df)

    # Extract cleaned names and mappings
    cleaned_names = result.df.columns.tolist()
    mappings = {}

    for original, cleaned in zip(column_names, cleaned_names):
        mappings[original] = cleaned

    return cleaned_names, mappings


def test_matcher_with_and_without_cleaning(
    matcher: HybridMatcher,
    df: pd.DataFrame,
    ground_truth: Dict[str, Tuple[str, str]],
    test_name: str,
    test_key: str
) -> Tuple[Dict, Dict, Dict[str, str]]:
    """
    Test matcher with both raw and cleaned column names.

    Returns:
        Tuple of (raw_result, cleaned_result, column_mappings)
    """
    original_columns = df.columns.tolist()

    # Clean the column names
    cleaned_columns, column_mappings = clean_column_names(original_columns)

    # Test with RAW column names
    print(f"\n{'='*80}")
    print(f"Testing RAW column names for {test_name}")
    print(f"{'='*80}")
    raw_result = test_matcher(matcher, original_columns, ground_truth, test_name, test_key, "RAW")

    # Test with CLEANED column names
    print(f"\n{'='*80}")
    print(f"Testing CLEANED column names for {test_name}")
    print(f"{'='*80}")

    # Need to update ground truth keys to use cleaned column names
    cleaned_ground_truth = {}
    for original_col, cleaned_col in column_mappings.items():
        if original_col in ground_truth:
            cleaned_ground_truth[cleaned_col] = ground_truth[original_col]

    cleaned_result = test_matcher(matcher, cleaned_columns, cleaned_ground_truth, test_name, test_key, "CLEANED")

    return raw_result, cleaned_result, column_mappings


def test_matcher(
    matcher: HybridMatcher,
    column_names: List[str],
    ground_truth: Dict[str, Tuple[str, str]],
    test_name: str,
    test_key: str,
    label: str
) -> Dict:
    """Test matcher against column names with ground truth."""
    correct = 0
    incorrect = 0
    missing = 0
    column_results = []

    print(f"\nColumns: {len(column_names)}")
    print(f"Ground truth entries: {len(ground_truth)}")
    print(f"Accuracy threshold: {get_threshold(test_key)*100:.0f}%")
    print("\nResults:")
    print("-" * 80)

    for column in column_names:
        expected = ground_truth.get(column)

        # Get match from hybrid matcher
        candidates = matcher.match(
            header=column,
            sheet_name=test_name,
            column_names=column_names
        )

        if candidates:
            predicted = (candidates[0]["model"], candidates[0]["field"])
            confidence = candidates[0]["confidence"]
            method = candidates[0]["method"]

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

                print(f"{status} | {column:30} → {predicted[0]:25}.{predicted[1] or 'None':25}")
                if status == "✗ WRONG  ":
                    print(f"         | Expected: {expected[0]:25}.{expected[1]:25}")

                column_results.append({
                    "column": column,
                    "expected_model": expected[0],
                    "expected_field": expected[1],
                    "predicted_model": predicted[0],
                    "predicted_field": predicted[1],
                    "confidence": confidence,
                    "method": method,
                    "status": status.split()[1],
                })
            else:
                print(f"  NO GT  | {column:30} → {predicted[0]:25}.{predicted[1] or 'None':25}")
        else:
            if expected:
                status = "✗ MISSING "
                missing += 1
                print(f"{status} | {column:30} → NO MATCH")
                column_results.append({
                    "column": column,
                    "expected_model": expected[0],
                    "expected_field": expected[1],
                    "predicted_model": None,
                    "predicted_field": None,
                    "confidence": 0.0,
                    "method": "none",
                    "status": "MISSING",
                })
            else:
                print(f"  NO GT  | {column:30} → NO MATCH")

    # Calculate metrics
    total = len(ground_truth)
    accuracy = correct / total if total > 0 else 0.0
    threshold = get_threshold(test_key)
    passed = accuracy >= threshold

    print("\n" + "-" * 80)
    print(f"{label} SUMMARY:")
    print(f"  Correct:   {correct}/{total} ({accuracy*100:.1f}%)")
    print(f"  Incorrect: {incorrect}/{total}")
    print(f"  Missing:   {missing}/{total}")
    print(f"  Accuracy:  {accuracy*100:.1f}%")
    print(f"  Status:    {'✓ PASS' if passed else '✗ FAIL'}")

    return {
        "label": label,
        "total_fields": total,
        "correct": correct,
        "incorrect": incorrect,
        "missing": missing,
        "accuracy": accuracy,
        "threshold": threshold,
        "passed": passed,
        "column_results": column_results,
    }


def test_precleaning_impact():
    """Run pre-cleaning impact test."""
    print("="*80)
    print("PRE-CLEANING IMPACT TEST")
    print("="*80)
    print(f"Testing: Matching accuracy with vs without column name pre-cleaning")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize HybridMatcher
    dictionary_path = Path(__file__).parent.parent.parent.parent / "odoo-dictionary"
    print(f"\nInitializing HybridMatcher with dictionary: {dictionary_path}")
    matcher = HybridMatcher(dictionary_path=dictionary_path)

    # Initialize results collector
    results = PreCleaningTestResults()

    # Test 1: Customers (should not change - no special chars in column names)
    print("\n" + "="*80)
    print("TEST 1: CUSTOMERS (res.partner)")
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

    raw_result, cleaned_result, mappings = test_matcher_with_and_without_cleaning(
        matcher, customer_df, GROUND_TRUTH["customers"], "Customers", "customers"
    )
    results.add_test_case(raw_result, cleaned_result, "Customers")

    print(f"\n{'='*40}")
    print(f"Column Mappings:")
    for orig, cleaned in mappings.items():
        if orig != cleaned:
            print(f"  {orig} → {cleaned}")
    if all(o == c for o, c in mappings.items()):
        print(f"  (No changes - column names were already clean)")
    print(f"{'='*40}")

    # Test 2: Leads (should improve - has " (Contact)" suffixes)
    print("\n" + "="*80)
    print("TEST 2: LEADS (crm.lead) - HAS PARENTHETICAL SUFFIXES")
    print("="*80)

    leads_df = pd.DataFrame({
        "Opportunity Title": ["Website Redesign", "ERP Implementation"],
        "Email": ["contact@prospect.com", "info@bigcorp.com"],
        "Phone": ["+1-555-0300", "+1-555-0400"],
        "Street Address (Contact)": ["789 Business Ave", "321 Commerce St"],
        "City (Contact)": ["Boston", "Chicago"],
        "Zip (Contact)": ["02101", "60601"],
        "Lead Status": ["Qualified", "New"],
        "Salesperson": ["Alice Johnson", "Bob Williams"],
        "Source": ["Website", "Referral"],
        "Expected Revenue": [50000, 100000],
    })

    raw_result, cleaned_result, mappings = test_matcher_with_and_without_cleaning(
        matcher, leads_df, GROUND_TRUTH["leads"], "Leads", "leads"
    )
    results.add_test_case(raw_result, cleaned_result, "Leads")

    print(f"\n{'='*40}")
    print(f"Column Mappings:")
    for orig, cleaned in mappings.items():
        if orig != cleaned:
            print(f"  {orig} → {cleaned}")
    print(f"{'='*40}")

    # Test 3: Simulated messy data (special characters, trailing dots, etc.)
    print("\n" + "="*80)
    print("TEST 3: PRODUCTS (product.product) - SIMULATED MESSY COLUMN NAMES")
    print("="*80)

    messy_products_df = pd.DataFrame({
        "Product Name...": ["Widget A", "Gadget B"],
        "SKU*": ["WID-001", "GAD-002"],
        "Sale Price?": [29.99, 49.99],
        "Cost Price (Internal)": [15.00, 25.00],
        "Category": ["Electronics", "Hardware"],
        "Barcode #": ["1234567890123", "9876543210987"],
        "Active": [True, True],
    })

    # Ground truth for messy products (maps to clean versions)
    messy_products_ground_truth = {
        "Product Name...": ("product.product", "name"),
        "SKU*": ("product.product", "default_code"),
        "Sale Price?": ("product.product", "list_price"),
        "Cost Price (Internal)": ("product.product", "standard_price"),
        "Category": ("product.product", "categ_id"),
        "Barcode #": ("product.product", "barcode"),
        "Active": ("product.product", "active"),
    }

    raw_result, cleaned_result, mappings = test_matcher_with_and_without_cleaning(
        matcher, messy_products_df, messy_products_ground_truth, "Products", "products"
    )
    results.add_test_case(raw_result, cleaned_result, "Products (Messy)")

    print(f"\n{'='*40}")
    print(f"Column Mappings:")
    for orig, cleaned in mappings.items():
        if orig != cleaned:
            print(f"  {orig} → {cleaned}")
    print(f"{'='*40}")

    # Finalize and print summary
    results.finalize()
    print_summary(results)

    return results


def print_summary(results: PreCleaningTestResults):
    """Print comprehensive summary."""
    summary = results.get_summary()

    print("\n" + "="*80)
    print("PRE-CLEANING IMPACT SUMMARY")
    print("="*80)

    print(f"\nOverall Results:")
    print(f"  Total Fields:      {summary['total_fields']}")
    print(f"  RAW Correct:       {summary['raw_correct']} ({summary['raw_accuracy']*100:.1f}%)")
    print(f"  CLEANED Correct:   {summary['cleaned_correct']} ({summary['cleaned_accuracy']*100:.1f}%)")
    print(f"  Improvement:       {summary['improvement']*100:+.1f} percentage points")

    print(f"\nPer-Test Case Breakdown:")
    print("-" * 80)
    print(f"{'Test Case':<30} {'RAW':<15} {'CLEANED':<15} {'Improvement'}")
    print("-" * 80)

    for test in results.test_cases:
        raw_acc = test["raw"]["accuracy"] * 100
        cleaned_acc = test["cleaned"]["accuracy"] * 100
        improvement = test["improvement"] * 100

        raw_status = "✓" if test["raw"]["passed"] else "✗"
        cleaned_status = "✓" if test["cleaned"]["passed"] else "✗"

        print(f"{test['test_name']:<30} {raw_status} {raw_acc:>5.1f}%        {cleaned_status} {cleaned_acc:>5.1f}%        {improvement:+6.1f}%")

    print("-" * 80)

    # Overall verdict
    print(f"\n{'='*80}")
    if summary['improvement'] > 0.05:
        print("✓✓✓ SIGNIFICANT IMPROVEMENT: Pre-cleaning improves accuracy by >5%!")
        print("    Recommendation: ENABLE pre-cleaning in production pipeline")
    elif summary['improvement'] > 0.01:
        print("✓✓ MODERATE IMPROVEMENT: Pre-cleaning improves accuracy by 1-5%")
        print("   Recommendation: Consider enabling pre-cleaning")
    elif summary['improvement'] > 0:
        print("✓ MINOR IMPROVEMENT: Pre-cleaning provides small improvement")
    else:
        print("⚠ NO IMPROVEMENT: Pre-cleaning does not improve accuracy")
        print("  This may indicate the test data is already clean")
    print(f"{'='*80}")
    print(f"\nDuration: {summary['duration_seconds']:.1f} seconds")


if __name__ == "__main__":
    results = test_precleaning_impact()

    # Save results
    summary = results.get_summary()

    print(f"\n{'='*80}")
    print(f"FINAL VERDICT:")
    print(f"  Pre-cleaning {'IMPROVES' if summary['improvement'] > 0 else 'DOES NOT IMPROVE'} matching accuracy")
    print(f"  Accuracy change: {summary['improvement']*100:+.1f} percentage points")
    print(f"{'='*80}")

    # Exit with success if improvement is positive
    sys.exit(0 if summary['improvement'] >= 0 else 1)
